def calculate_kbju(gender: str, weight: float, height: float, age: int, activity: str, goal: str):
    if gender.lower() in ("мужской", "male", "m"):
        bmr = (10 * weight) + (6.25 * height) - (5 * age) + 5
    else:
        bmr = (10 * weight) + (6.25 * height) - (5 * age) - 161
        
    mults = {"sedentary": 1.2, "light": 1.375, "moderate": 1.55, "active": 1.725}
    tdee = bmr * mults.get(activity, 1.375)
    
    if "похудение" in goal.lower() or "deficit" in goal.lower():
        calories = round(tdee * 0.82)
    elif "набор" in goal.lower() or "surplus" in goal.lower():
        calories = round(tdee * 1.12)
    else:
        calories = round(tdee)
        
    protein = round((calories * 0.30) / 4)
    fats = round((calories * 0.25) / 9)
    carbs = round((calories * 0.45) / 4)
    water_liters = round(weight * 0.033, 1)
    
    return {
        "bmr": round(bmr),
        "tdee": round(tdee),
        "calories": calories,
        "protein": protein,
        "fats": fats,
        "carbs": carbs,
        "water": water_liters
    }
