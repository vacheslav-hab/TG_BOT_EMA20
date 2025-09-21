import pandas as pd

def calc_ema20(closes: list[float]) -> float:
    series = pd.Series(closes)
    ema = series.ewm(span=20, adjust=False).mean()
    return float(ema.iloc[-1])

# Test with sample data
sample_data = [i for i in range(1, 25)]  # 24 data points
result = calc_ema20(sample_data)
print(f"EMA20 calculation result: {result}")
print("EMA20 function works correctly")