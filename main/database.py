import os
from datetime import datetime
from sqlalchemy import create_engine, text, Column, Integer, String, Float, Text
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class UserProfile(Base):
    __tablename__ = 'user_profile'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    weight = Column(Float, default=70.0)
    height = Column(Float, default=175.0)
    age = Column(Integer, default=20)
    gender = Column(String, default="Male") # 'Male' or "Female"
    activity_level = Column(String, default="moderate") # 'sedentary', 'moderate', 'active', 'very_active'
    goal = Column(String, default="maintenance")     # 'weight_loss', 'maintenance', 'muscle_gain'
    dietary_restrictions = Column(String, default="")

    target_calories = Column(Integer, default=2000)
    target_protein = Column(Integer, default=150)
    target_fat = Column(Integer, default=70)
    target_carbs = Column(Integer, default=250)

    def calculate_and_update_targets(self):
        """
        Metoda wywoływana przy zapisie. Przelicza BMR, TDEE i makro.
        """
        # 1. BMR (Mifflin-St Jeor)
        if self.gender == 'Male':
            bmr = (10 * self.weight) + (6.25 * self.height) - (5 * self.age) + 5
        else:
            bmr = (10 * self.weight) + (6.25 * self.height) - (5 * self.age) - 161
            
        # 2. TDEE (Zapotrzebowanie całkowite)
        multipliers = {'sedentary': 1.2, 
                       'moderate': 1.375, 
                       'active': 1.55, 
                       'very_active': 1.725}
        tdee = bmr * multipliers.get(self.activity_level, 1.2)
        
        # 3. Dostosowanie Kalorii do Celu
        if self.goal == 'weight_loss':
            self.target_calories = int(tdee - 400)
        elif self.goal == 'muscle_gain':
            self.target_calories = int(tdee + 300)
        else:
            self.target_calories = int(tdee)

        # 4. Makroskładniki
        # Klucz: (Białko %, Tłuszcze %, Węgle %)
        macro_ratios = {
            'sedentary':    (0.25, 0.35, 0.40), # Mniej węgli, więcej tłuszczu
            'moderate':     (0.30, 0.30, 0.40), # Zbalansowane
            'active':       (0.30, 0.25, 0.45), # Więcej węgli na trening
            'very_active':  (0.25, 0.20, 0.55)  # Paliwo (glikogen)
        }
        
        # Pobieramy proporcje dla wybranej aktywności
        p_r, f_r, c_r = macro_ratios.get(self.activity_level, (0.3, 0.3, 0.4))
        
        # Przeliczamy na gramy (Białko/Węgle/4, Tłuszcz /9)
        self.target_protein = int((self.target_calories * p_r) / 4)
        self.target_fat = int((self.target_calories * f_r) / 9)
        self.target_carbs = int((self.target_calories * c_r) / 4)

class MealLog(Base):
    """
    Tabela historii posiłków (Dziennik).
    """
    __tablename__ = 'meal_log'

    id = Column(Integer, primary_key=True)
    # Zapisujemy datę jako string ISO (SQLite nie ma typu Date)
    date = Column(String, default=lambda: datetime.now().isoformat())

    recipe_name = Column(String)
    recipe_url = Column(String)     
    image_url = Column(String)

    calories = Column(Float)
    protein = Column(Float)
    carbs = Column(Float)
    fat = Column(Float)
    
    user_rating = Column(Integer)   # Ocena 1-10
    user_notes = Column(Text, nullable=True)

DB_URL = "sqlite:///nowaste.db"
engine = create_engine(DB_URL, connect_args={"check_same_thread": False})

SessionLocal = sessionmaker(bind=engine, autoflush=False)

def init_db():
    Base.metadata.create_all(engine)

def get_db():
    return SessionLocal()