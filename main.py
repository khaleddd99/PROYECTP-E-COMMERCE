import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional
from abc import ABC, abstractmethod # Necesario para las INTERFACES
import datetime

# ==========================================
# 1. MODELOS DE DATOS (Entidades)
# ==========================================
# Seguimos usando Pydantic para validar los datos que entran y salen.

class Producto(BaseModel):
    model_config = ConfigDict(frozen=True) # Inmutable
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

# ==========================================
# 2. DEFINICIÓN DE INTERFACES (Abstracción)
# ==========================================
# Cumple con: "Implementar interfaces"
# Define QUÉ debe hacer el sistema, sin decir CÓMO.

class IEcommerce(ABC):
    
    @abstractmethod
    def obtener_productos(self) -> List[Producto]:
        pass

    @abstractmethod
    def agregar_producto(self, producto: Producto) -> Producto:
        pass

    @abstractmethod
    def gestionar_carrito(self, carrito_id: int, item: ItemCarrito) -> Carrito:
        pass

    @abstractmethod
    def realizar_checkout(self, carrito_id: int) -> Pedido:
        pass

# ==========================================
# 3. CLASE DEL SISTEMA (Encapsulación)
# ==========================================
# Cumple con: "Implementar encapsulación" y "Manejo de errores"
# Aquí está la lógica real, protegiendo los datos con guiones bajos (_variable).

class SistemaEcommerce(IEcommerce):
    def __init__(self):
        # ENCAPSULACIÓN: Usamos variables "privadas" (con _) para que
        # nadie las modifique directamente desde fuera de la clase.
        self._db_productos: List[Producto] = [
            Producto(id=1, nombre="Laptop Gamer", precio=1200.00, stock=10),
            Producto(id=2, nombre="Teclado Mecánico", precio=150.00, stock=25),
            Producto(id=3, nombre="Mouse Óptico", precio=45.50, stock=50),
        ]
        self._db_carritos: List[Carrito] = [Carrito(id=1)]
        self._db_pedidos: List[Pedido] = []

    # --- MÉTODOS PÚBLICOS ---

    def obtener_productos(self) -> List[Producto]:
        """Retorna la lista actual de productos."""
        return self._db_productos

    def agregar_producto(self, producto: Producto) -> Producto:
        """
        Agrega un producto nuevo validando que el ID no exista.
        Manejo de Errores: Lanza excepción si hay duplicados.
        """
        # Verificamos si ya existe (Manejo de errores lógico)
        for p in self._db_productos:
            if p.id == producto.id:
                raise ValueError(f"El producto con ID {producto.id} ya existe.")
        
        self._db_productos.append(producto)
        return producto

    def gestionar_carrito(self, carrito_id: int, item: ItemCarrito) -> Carrito:
        """
        Agrega items al carrito y recalcula totales.
        """
        try:
            # 1. Buscar Carrito
            carrito = next((c for c in self._db_carritos if c.id == carrito_id), None)
            if not carrito:
                raise ValueError("Carrito no encontrado.")

            # 2. Buscar Producto y Validar Stock
            producto = next((p for p in self._db_productos if p.id == item.producto_id), None)
            if not producto:
                raise ValueError("Producto no encontrado.")
            
            if producto.stock < item.cantidad:
                raise ValueError(f"Stock insuficiente para {producto.nombre}.")

            # 3. Actualizar lógica del carrito (Lógica de negocio)
            # Buscamos si el item ya está en el carrito para sumar cantidad
            item_existente = False
            nuevos_items = []
            for i in carrito.items:
                if i.producto_id == item.producto_id:
                    nuevos_items.append(ItemCarrito(producto_id=i.producto_id, cantidad=i.cantidad + item.cantidad))
                    item_existente = True
                else:
                    nuevos_items.append(i)
            
            if not item_existente:
                nuevos_items.append(item)

            carrito.items = nuevos_items
            
            # Recalcular Total
            total = 0.0
            for i in carrito.items:
                prod = next(p for p in self._db_productos if p.id == i.producto_id)
                total += prod.precio * i.cantidad
            
            carrito.total = round(total, 2)
            return carrito

        except Exception as e:
            # Re-lanzamos el error para que la API lo capture
            print(f"Error en gestionar_carrito: {str(e)}") # Log interno
            raise e

    def realizar_checkout(self, carrito_id: int) -> Pedido:
        """
        Procesa el pedido, descuenta stock y limpia el carrito.
        Cumple con la lógica compleja y manejo de estado.
        """
        # 1. Validaciones
        carrito = next((c for c in self._db_carritos if c.id == carrito_id), None)
        if not carrito:
            raise ValueError("Carrito no encontrado.")
        if not carrito.items:
            raise ValueError("El carrito está vacío.")

        # 2. Descontar Stock (Operación Crítica)
        # Usamos una lista temporal para asegurar atomicidad (o todo o nada)
        nuevos_productos = self._db_productos.copy()
        
        for item in carrito.items:
            for idx, prod in enumerate(nuevos_productos):
                if prod.id == item.producto_id:
                    # Creamos una copia del producto con el stock restado
                    nuevo_stock = prod.stock - item.cantidad
                    nuevos_productos[idx] = prod.model_copy(update={'stock': nuevo_stock})
                    break
        
        # 3. Confirmar cambios en la "Base de Datos" (Encapsulada)
        self._db_productos = nuevos_productos

        # 4. Crear Pedido
        nuevo_pedido = Pedido(
            id=len(self._db_pedidos) + 1,
            items=carrito.items, # Guardamos copia de los items
            total_pedido=carrito.total,
            fecha=datetime.datetime.now().isoformat(),
            estado="Completado"
        )
        self._db_pedidos.append(nuevo_pedido)

        # 5. Limpiar Carrito
        carrito.items = []
        carrito.total = 0.0

        return nuevo_pedido

# ==========================================
# 4. INSTANCIACIÓN Y API (FastAPI)
# ==========================================

app = FastAPI(title="Sistema E-commerce POO", description="Implementación con Clases e Interfaces")

# Instanciamos nuestra clase principal.
# Ahora 'sistema' es un OBJETO que contiene todos los datos y lógica.
sistema = SistemaEcommerce()

@app.get("/productos", response_model=List[Producto])
async def api_obtener_productos():
    return sistema.obtener_productos()

@app.post("/productos", response_model=Producto)
async def api_crear_producto(producto: Producto):
    try:
        return sistema.agregar_producto(producto)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/carrito/{carrito_id}/agregar", response_model=Carrito)
async def api_agregar_carrito(carrito_id: int, item: ItemCarrito):
    try:
        return sistema.gestionar_carrito(carrito_id, item)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/carrito/{carrito_id}/checkout", response_model=Pedido)
async def api_checkout(carrito_id: int):
    try:
        return sistema.realizar_checkout(carrito_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error interno del servidor")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
