import pytest

from sda.core.domain.errors import GenerationError
from sda.core.generation.generator import DataGenerator


def test_orders_linked_to_users_and_products() -> None:
    """Заказы должны ссылаться только на сгенерированных пользователей и товары."""
    generator = DataGenerator()
    
    generator.generate_table("users", 3)
    generator.generate_table("products", 2)
    
    valid_users = {u["user_id"] for u in generator.context["users"]}
    valid_products = {p["product_id"] for p in generator.context["products"]}
    
    orders = generator.generate_table("orders", 10)
    
    for order in orders:
        assert order["user_id"] in valid_users
        assert order["product_id"] in valid_products


def test_payments_strict_consistency() -> None:
    """
    Платеж должен ссылаться на заказ, а user_id платежа должен 
    строго совпадать с владельцем этого заказа.
    """
    generator = DataGenerator()
    
    generator.generate_table("users", 3)
    generator.generate_table("products", 2)
    generator.generate_table("orders", 5)
  
    order_user_map = {o["order_id"]: o["user_id"] for o in generator.context["orders"]}
    
    payments = generator.generate_table("payments", 10)
    
    for payment in payments:
        p_order_id = payment["order_id"]
        p_user_id = payment["user_id"]
        
        assert p_order_id in order_user_map
        assert p_user_id == order_user_map[p_order_id]


def test_missing_context_raises_error() -> None:
    """Проверка защиты: генерация зависимой таблицы без родительской вызывает ошибку."""
    generator = DataGenerator()
    
    with pytest.raises(GenerationError, match="контекст users пуст"):
        generator.generate_table("orders", 5)
        
    generator.generate_table("users", 2)
    
    with pytest.raises(GenerationError, match="контекст products пуст"):
        generator.generate_table("orders", 5)

    generator.generate_table("products", 2)
    generator.generate_table("orders", 2)
    
    generator.context["orders"] = []
    with pytest.raises(GenerationError, match="без ранее созданных orders"):
        generator.generate_table("payments", 5)


def test_unsupported_context_ref_raises_error() -> None:
    """Проверка обработки неизвестных ссылок (защита от опечаток в JSON)."""
    generator = DataGenerator()
    col = {"name": "bad_ref", "provider": "context_ref", "ref": "unknown_entity_id"}
    
    with pytest.raises(GenerationError, match="Неподдерживаемая ссылка на контекст 'unknown_entity_id'"):
        generator._resolve_context_ref("test_table", col)