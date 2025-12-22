from fastapi.testclient import TestClient
from main import app

# Creamos un "Cliente de Prueba" basado en tu aplicación
client = TestClient(app)

# 1. Prueba: Verificar que la lista de productos carga bien
def test_leer_productos():
    response = client.get("/productos")
    # Esperamos código 200 (Éxito)
    assert response.status_code == 200
    # Esperamos que haya al menos 3 productos (Laptop, Teclado, Mouse)
    assert len(response.json()) >= 3

# 2. Prueba: Verificar que podemos ver un producto específico
def test_leer_producto_individual():
    response = client.get("/productos/1")
    assert response.status_code == 200
    assert response.json()["nombre"] == "Laptop Gamer"

# 3. Prueba: Flujo completo de agregar al carrito
def test_agregar_carrito():
    # Intentamos agregar 1 Teclado (ID 2) al carrito 1
    payload = {"producto_id": 2, "cantidad": 1}
    response = client.post("/carrito/1/agregar", json=payload)
    
    assert response.status_code == 200
    # Verificamos que el total sea 150.0 (Precio del teclado)
    assert response.json()["total"] == 150.0

# 4. Prueba: Verificar que el carrito existe
def test_ver_carrito():
    response = client.get("/carrito/1")
    assert response.status_code == 200
    assert "items" in response.json()
