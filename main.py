# main.py
from readExcel import read_and_validate_tasks

def main():
    tasks = read_and_validate_tasks("ExampleTimeline.xlsx", sheet_name="Sheet1")
    print(f"Loaded {len(tasks)} tasks successfully.")

if __name__ == "__main__":
    main()