import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid

def generate_workout_data(num_records=100):
    """Generate realistic-looking workout data for testing."""
    
    # Create date range for the past year
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365)
    dates = pd.date_range(start=start_date, end=end_date, periods=num_records)
    
    # Generate random but realistic workout data
    data = {
        'workout_id': [str(uuid.uuid4()) for _ in range(num_records)],
        'workout_date': dates,
        'distance_mi': np.random.uniform(2.0, 10.0, num_records),  # Miles
        'duration_sec': np.random.uniform(1200, 3600, num_records),  # 20-60 minutes
        'kcal_burned': np.random.uniform(200, 800, num_records),
    }
    
    # Create DataFrame
    df = pd.DataFrame(data)
    
    # Calculate derived metrics
    df['avg_pace'] = df['distance_mi'] / (df['duration_sec'] / 3600)  # mph
    df['max_pace'] = df['avg_pace'] * np.random.uniform(1.1, 1.3, num_records)  # Slightly faster than average
    
    # Round numeric columns to 2 decimal places
    numeric_columns = ['distance_mi', 'avg_pace', 'max_pace', 'kcal_burned']
    df[numeric_columns] = df[numeric_columns].round(2)
    
    return df

def main():
    """Generate test data files."""
    # Generate three months of data with different file names
    for month in range(3):
        df = generate_workout_data(num_records=30)  # 30 records per month
        
        # Save as CSV
        filename = f'workout_data_{datetime.now().strftime("%Y%m")}_{month+1}.csv'
        df.to_csv(filename, index=False)
        print(f"Generated {filename} with {len(df)} records")

if __name__ == "__main__":
    main()