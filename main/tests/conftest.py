import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from main.database import Base
import sys, os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

@pytest.fixture(scope="function")
def test_db():
    """
    Tworzy nową bazę danych w pamięci RAM dla każdego testu.
    Dzięki temu testy są szybkie i nie wpływają na siebie nawzajem.
    """
    # Używamy SQLite w pamięci (:memory:)
    engine = create_engine("sqlite:///:memory:")
    
    # Tworzymy tabele
    Base.metadata.create_all(engine)
    
    # Tworzymy sesję
    Session = sessionmaker(bind=engine)
    session = Session()
    
    yield session  # Tu wykonuje się test
    
    # Sprzątanie po teście
    session.close()
    Base.metadata.drop_all(engine)