import uvicorn
import asyncio  # IMPORTANTE: Esto permite la concurrencia
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from abc import ABC, abstractmethod
import datetime

# --- 1. MODELOS DE DATOS (Pydantic serializa a JSON automáticamente) ---

class Producto(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    nombre: str
    precio: float
    stock: int

class ItemCarrito(BaseModel):
    model_config = ConfigDict(frozen=True)
    producto_id: int
    cantidad: int

class Carrito(BaseModel):
    id: int
    items: List[ItemCarrito] = Field(default_factory=list)
    total: float = 0.0

class Pedido(BaseModel):
    id: int
    items: List[ItemCarrito]
    total_pedido: float
    fecha: str
    estado: str

# --- 2. INTERFAZ (Cumple requisito POO) ---

class IEcommerce(ABC):
    @abstractmethod
    def obtener_productos(self) -> List[Producto]: pass
    @abstractmethod
    def obtener_producto_por_id(self, pid: int) -> Producto: pass 
    @abstractmethod
    def agregar_producto(self, producto: Producto) -> Producto: pass
    @abstractmethod
    def gestionar_carrito(self, carrito_id: int, item: ItemCarrito) -> Carrito: pass
    @abstractmethod
    def vaciar_carrito(self, carrito_id: int) -> Carrito: pass 
    @abstractmethod
    def realizar_checkout(self, carrito_id: int) -> Pedido: pass
    @abstractmethod
    def obtener_pedidos(self) -> List[Pedido]: pass 

# --- 3. CLASE SISTEMA (Lógica encapsulada) ---

class SistemaEcommerce(IEcommerce):
    def __init__(self):
        # Base de datos simulada en memoria
        self._db_productos: List[Producto] = [
            Producto(id=1, nombre="Laptop Gamer", precio=1200.00, stock=10),
            Producto(id=2, nombre="Teclado Mecánico", precio=150.00, stock=25),
            Producto(id=3, nombre="Mouse Óptico", precio=45.50, stock=50),
        ]
        self._db_carritos: List[Carrito] = [Carrito(id=1)]
        self._db_pedidos: List[Pedido] = []

    def obtener_productos(self) -> List[Producto]:
        return self._db_productos

    def obtener_producto_por_id(self, pid: int) -> Producto:
        # Busca un producto específico
        prod = next((p for p in self._db_productos if p.id == pid), None)
        if not prod: raise ValueError("Producto no encontrado")
        return prod

    def agregar_producto(self, producto: Producto) -> Producto:
        if any(p.id == producto.id for p in self._db_productos):
            raise ValueError(f"El producto ID {producto.id} ya existe.")
        self._db_productos.append(producto)
        return producto

    def gestionar_carrito(self, carrito_id: int, item: ItemCarrito) -> Carrito:
        carrito = next((c for c in self._db_carritos if c.id == carrito_id), None)
        if not carrito: raise ValueError("Carrito no encontrado.")
        
        producto = next((p for p in self._db_productos if p.id == item.producto_id), None)
        if not producto: raise ValueError("Producto no encontrado.")
        if producto.stock < item.cantidad: raise ValueError("Stock insuficiente.")

        # Lógica para sumar cantidad si el item ya existe
        nuevos_items = []
        encontrado = False
        for i in carrito.items:
            if i.producto_id == item.producto_id:
                nuevos_items.append(ItemCarrito(producto_id=i.producto_id, cantidad=i.cantidad + item.cantidad))
                encontrado = True
            else:
                nuevos_items.append(i)
        if not encontrado: nuevos_items.append(item)
        
        carrito.items = nuevos_items
        # Recalcular total usando programación funcional (sum y map)
        total = sum(next(p.precio for p in self._db_productos if p.id == i.producto_id) * i.cantidad for i in carrito.items)
        carrito.total = round(total, 2)
        return carrito

    def vaciar_carrito(self, carrito_id: int) -> Carrito:
        carrito = next((c for c in self._db_carritos if c.id == carrito_id), None)
        if not carrito: raise ValueError("Carrito no encontrado.")
        carrito.items = []
        carrito.total = 0.0
        return carrito

    def realizar_checkout(self, carrito_id: int) -> Pedido:
        carrito = next((c for c in self._db_carritos if c.id == carrito_id), None)
        if not carrito or not carrito.items: raise ValueError("Carrito vacío o no encontrado.")
        
        # Descontar stock
        for item in carrito.items:
            for idx, prod in enumerate(self._db_productos):
                if prod.id == item.producto_id:
                    self._db_productos[idx] = prod.model_copy(update={'stock': prod.stock - item.cantidad})
        
        # Crear Pedido
        nuevo_pedido = Pedido(
            id=len(self._db_pedidos) + 1,
            items=carrito.items,
            total_pedido=carrito.total,
            fecha=datetime.datetime.now().isoformat(),
            estado="Completado"
        )
        self._db_pedidos.append(nuevo_pedido)
        self.vaciar_carrito(carrito_id)
        return nuevo_pedido

    def obtener_pedidos(self) -> List[Pedido]:
        return self._db_pedidos

# --- 4. API (Los 8 Servicios Web Requeridos) ---

app = FastAPI(title="Sistema E-commerce Final", description="Integra POO, Concurrencia y Testing")
sistema = SistemaEcommerce()

# Servicio 1: Listar
@app.get("/productos", response_model=List[Producto])
async def listar_productos():
    return sistema.obtener_productos()

# Servicio 2: Detalle (NUEVO)
@app.get("/productos/{pid}", response_model=Producto)
async def ver_producto(pid: int):
    try: return sistema.obtener_producto_por_id(pid)
    except ValueError as e: raise HTTPException(404, str(e))

# Servicio 3: Crear
@app.post("/productos", response_model=Producto)
async def crear_producto(producto: Producto):
    try: return sistema.agregar_producto(producto)
    except ValueError as e: raise HTTPException(400, str(e))

# Servicio 4: Ver Carrito (NUEVO)
@app.get("/carrito/{carrito_id}", response_model=Carrito)
async def ver_carrito(carrito_id: int):
    c = next((c for c in sistema._db_carritos if c.id == carrito_id), None)
    if not c: raise HTTPException(404, "Carrito no existe")
    return c

# Servicio 5: Agregar Item
@app.post("/carrito/{carrito_id}/agregar", response_model=Carrito)
async def agregar_item(carrito_id: int, item: ItemCarrito):
    try: return sistema.gestionar_carrito(carrito_id, item)
    except ValueError as e: raise HTTPException(400, str(e))

# Servicio 6: Vaciar Carrito (NUEVO - DELETE)
@app.delete("/carrito/{carrito_id}", response_model=Carrito)
async def limpiar_carrito(carrito_id: int):
    try: return sistema.vaciar_carrito(carrito_id)
    except ValueError as e: raise HTTPException(404, str(e))

# Servicio 7: Checkout con CONCURRENCIA
@app.post("/carrito/{carrito_id}/checkout", response_model=Pedido)
async def procesar_compra(carrito_id: int):
    try:
        # Aquí simulamos la espera de 2 segundos (el banco respondiendo)
        # Al usar 'await', el servidor queda libre para atender a otros mientras espera.
        await asyncio.sleep(2) 
        return sistema.realizar_checkout(carrito_id)
    except ValueError as e: raise HTTPException(400, str(e))

# Servicio 8: Historial (NUEVO)
@app.get("/pedidos", response_model=List[Pedido])
async def listar_pedidos():
    return sistema.obtener_pedidos()

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)

