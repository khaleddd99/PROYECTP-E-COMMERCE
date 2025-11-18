import uvicorn
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Optional, Tuple
import functools 
import datetime 


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
    model_config = ConfigDict(frozen=True)
    id: int
    items: List[ItemCarrito] = Field(default_factory=list)
    total: float = 0.0

class ItemPedido(BaseModel):
    model_config = ConfigDict(frozen=True)
    producto_id: int
    cantidad: int
    precio_congelado: float 

class Pedido(BaseModel):
    model_config = ConfigDict(frozen=True)
    id: int
    items: List[ItemPedido]
    total_pedido: float
    fecha: str
    estado: str 



db_productos: List[Producto] = [
    Producto(id=1, nombre="Laptop Gamer", precio=1200.00, stock=10),
    Producto(id=2, nombre="Teclado Mecánico", precio=150.00, stock=25),
    Producto(id=3, nombre="Mouse Óptico", precio=45.50, stock=50),
]

db_carritos: List[Carrito] = [
    Carrito(id=1) 
]

db_pedidos: List[Pedido] = []


app = FastAPI(
    title="API de Gestión de E-commerce",
    description="Proyecto de Programación Funcional"
)



def fn_buscar_producto(lista_productos: List[Producto], id_producto: int) -> Optional[Producto]:
    encontrados = list(filter(lambda p: p.id == id_producto, lista_productos))
    return encontrados[0] if encontrados else None

def fn_actualizar_stock(lista_productos: List[Producto], id_producto: int, cantidad_a_restar: int) -> List[Producto]:
    return [
        p
        if p.id != id_producto
        else p.model_copy(update={'stock': p.stock - cantidad_a_restar})
        for p in lista_productos
    ]

def fn_agregar_producto(lista_productos: List[Producto], producto_nuevo: Producto) -> List[Producto]:
    return lista_productos + [producto_nuevo]



def fn_buscar_carrito(lista_carritos: List[Carrito], carrito_id: int) -> Optional[Carrito]:
    encontrados = list(filter(lambda c: c.id == carrito_id, lista_carritos))
    return encontrados[0] if encontrados else None

def fn_recalcular_total(carrito: Carrito, lista_productos: List[Producto]) -> float:
    def obtener_precio(item: ItemCarrito) -> float:
        producto = fn_buscar_producto(lista_productos, item.producto_id)
        return (producto.precio * item.cantidad) if producto else 0.0
    subtotales = map(obtener_precio, carrito.items)
    total = sum(subtotales)
    return round(total, 2) 

def fn_agregar_item_al_carrito(
    carrito: Carrito, 
    item_nuevo: ItemCarrito, 
    lista_productos: List[Producto]
) -> Carrito:
    item_existente = next(
        (item for item in carrito.items if item.producto_id == item_nuevo.producto_id), 
        None
    )
    if item_existente:
        nueva_lista_items = [
            item.model_copy(update={'cantidad': item.cantidad + item_nuevo.cantidad})
            if item.producto_id == item_nuevo.producto_id
            else item
            for item in carrito.items
        ]
    else:
        nueva_lista_items = carrito.items + [item_nuevo]

    carrito_con_items_actualizados = carrito.model_copy(update={'items': nueva_lista_items})
    nuevo_total = fn_recalcular_total(carrito_con_items_actualizados, lista_productos)
    return carrito_con_items_actualizados.model_copy(update={'total': nuevo_total})

def fn_actualizar_carrito_en_db(lista_carritos: List[Carrito], carrito_actualizado: Carrito) -> List[Carrito]:
    return [
        carrito_actualizado if c.id == carrito_actualizado.id else c
        for c in lista_carritos
    ]

def fn_limpiar_carrito(carrito: Carrito) -> Carrito:
    """Devuelve una copia del carrito, pero vacío."""
    return carrito.model_copy(update={'items': [], 'total': 0.0})



def fn_convertir_carrito_a_pedido(
    carrito: Carrito, 
    lista_productos: List[Producto],
    nuevo_id_pedido: int
) -> Pedido:
    """
    Convierte los items del carrito en items de pedido,
    "congelando" el precio. Función pura.
    """
    items_pedido: List[ItemPedido] = []
    for item_c in carrito.items:
        producto = fn_buscar_producto(lista_productos, item_c.producto_id)
        if producto:
            item_p = ItemPedido(
                producto_id=item_c.producto_id,
                cantidad=item_c.cantidad,
                precio_congelado=producto.precio
            )
            items_pedido.append(item_p)
            
    return Pedido(
        id=nuevo_id_pedido,
        items=items_pedido,
        total_pedido=carrito.total,
        fecha=datetime.datetime.now().isoformat(),
        estado="Pendiente"
    )

def fn_descontar_stock_de_pedido(
    lista_productos: List[Producto], 
    carrito: Carrito
) -> List[Producto]:
    """
    Esta es una función funcional clave. Usa 'reduce' para
    aplicar la función 'fn_actualizar_stock' secuencialmente
    para cada item en el carrito.
    
    Toma la lista de productos inicial y la va "reduciendo"
    a una nueva lista con el stock actualizado.
    """
    
    def reducer(
        productos_acumulados: List[Producto], 
        item_actual: ItemCarrito             
    ) -> List[Producto]:
        
        return fn_actualizar_stock(
            productos_acumulados, 
            item_actual.producto_id, 
            item_actual.cantidad
        )

    nueva_lista_productos = functools.reduce(
        reducer,
        carrito.items,
        lista_productos 
    )
    
    return nueva_lista_productos

def fn_agregar_pedido_a_db(lista_pedidos: List[Pedido], pedido: Pedido) -> List[Pedido]:
    """Devuelve una nueva lista de pedidos con el nuevo pedido añadido."""
    return lista_pedidos + [pedido]


@app.get("/productos", response_model=List[Producto])
async def obtener_todos_los_productos():
    return db_productos

@app.get("/productos/{producto_id}", response_model=Producto)
async def obtener_producto_por_id(producto_id: int):
    producto = fn_buscar_producto(db_productos, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    return producto

@app.post("/productos", response_model=Producto, status_code=201)
async def crear_nuevo_producto(producto: Producto):
    global db_productos
    if fn_buscar_producto(db_productos, producto.id):
        raise HTTPException(status_code=400, detail="ID de producto ya existe")
    db_productos = fn_agregar_producto(db_productos, producto)
    return producto

@app.put("/productos/{producto_id}/descontar-stock", response_model=Producto)
async def descontar_stock_de_producto(producto_id: int, cantidad: int):
    global db_productos
    producto = fn_buscar_producto(db_productos, producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if producto.stock < cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")
    db_productos = fn_actualizar_stock(db_productos, producto_id, cantidad)
    return fn_buscar_producto(db_productos, producto_id)

@app.get("/carrito/{carrito_id}", response_model=Carrito)
async def obtener_carrito(carrito_id: int):
    carrito = fn_buscar_carrito(db_carritos, carrito_id)
    if not carrito:
        raise HTTPException(status_code=404, detail="Carrito no encontrado")
    return carrito

@app.post("/carrito/{carrito_id}/agregar", response_model=Carrito)
async def agregar_item_al_carrito(carrito_id: int, item: ItemCarrito):
    global db_carritos
    carrito_actual = fn_buscar_carrito(db_carritos, carrito_id)
    if not carrito_actual:
        raise HTTPException(status_code=404, detail="Carrito no encontrado")
    producto = fn_buscar_producto(db_productos, item.producto_id)
    if not producto:
        raise HTTPException(status_code=404, detail="Producto no encontrado")
    if producto.stock < item.cantidad:
        raise HTTPException(status_code=400, detail="Stock insuficiente")
    carrito_actualizado = fn_agregar_item_al_carrito(carrito_actual, item, db_productos)
    db_carritos = fn_actualizar_carrito_en_db(db_carritos, carrito_actualizado)
    return carrito_actualizado



@app.get("/pedidos", response_model=List[Pedido])
async def obtener_todos_los_pedidos():
    """Obtiene la lista de todos los pedidos creados."""
    return db_pedidos

@app.post("/carrito/{carrito_id}/checkout", response_model=Pedido)
async def procesar_checkout_carrito(carrito_id: int):
    """
    Crea un Pedido a partir de un Carrito, descuenta el stock
    y limpia el carrito. Esta es la operación "impura"
    que orquesta todas nuestras funciones puras.
    """

    global db_productos
    global db_carritos
    global db_pedidos
    
    carrito = fn_buscar_carrito(db_carritos, carrito_id)
    if not carrito:
        raise HTTPException(status_code=404, detail="Carrito no encontrado")
    if not carrito.items:
        raise HTTPException(status_code=400, detail="El carrito está vacío")

   
    nueva_lista_productos = fn_descontar_stock_de_pedido(db_productos, carrito)
    
    nuevo_id = len(db_pedidos) + 1

    nuevo_pedido = fn_convertir_carrito_a_pedido(carrito, db_productos, nuevo_id)
    
    nueva_lista_pedidos = fn_agregar_pedido_a_db(db_pedidos, nuevo_pedido)
    
    carrito_limpiado = fn_limpiar_carrito(carrito)
    
    nueva_lista_carritos = fn_actualizar_carrito_en_db(db_carritos, carrito_limpiado)
    
    db_productos = nueva_lista_productos
    db_pedidos = nueva_lista_pedidos
    db_carritos = nueva_lista_carritos
    
    return nuevo_pedido


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)