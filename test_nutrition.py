from app import calculate_nutrition

def test_nutrition():
    test_cases = [
        ("소고기 짜장면 100g", 12, "보통"),
        ("소고기죽 100g", 12, "보통"),
        ("사과 50g", 6, "보통"),
        ("볶음밥", 24, "보통"),
    ]
    
    print("\nNutritional Analysis Test Results:")
    print("=" * 50)
    for menu, months, amount in test_cases:
        res = calculate_nutrition(menu, months, amount)
        print(f"Menu: {menu}")
        print(f"Stage: {months} months, Amount: {amount}")
        print(f"Result: {res}")
        print("-" * 50)

if __name__ == "__main__":
    test_nutrition()
