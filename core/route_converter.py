import pandas as pd
import sys

def load_data(file_path):
    try:
        # Load the excel file
        # Assuming the first sheet is the correct one
        df = pd.read_excel(file_path)
        
        # Clean column names (strip whitespace)
        df.columns = df.columns.astype(str).str.strip()
        
        # Standardize crucial columns
        # We need ENR_NM (Airway), SEQ (Sequence), and Fix Name (likely FIXPNT based on inspection)
        # Let's handle variations just in case
        fix_col = None
        if 'FIXPNT' in df.columns:
            fix_col = 'FIXPNT'
        elif 'FIX_NM' in df.columns:
            fix_col = 'FIX_NM'
        elif 'POINT_NM' in df.columns:
            fix_col = 'POINT_NM'
            
        if not fix_col:
            raise ValueError(f"Could not find Fix/Point Name column. Available columns: {list(df.columns)}")
            
        # Ensure SEQ is numeric
        df['SEQ'] = pd.to_numeric(df['SEQ'], errors='coerce')
        
        # Normalize text to uppercase for easier matching
        df['ENR_NM'] = df['ENR_NM'].astype(str).str.upper().str.strip()
        df[fix_col] = df[fix_col].astype(str).str.upper().str.strip()
        
        return df, fix_col
    except Exception as e:
        print(f"Error loading data: {e}")
        sys.exit(1)

def expand_route(df, fix_col, route_str):
    tokens = route_str.strip().split()
    if not tokens:
        return []

    # Normalize column names to uppercase for consistent access
    # Handle both database (lowercase) and Excel (uppercase) column names
    df = df.copy()
    df.columns = df.columns.str.upper()

    # Normalize fix_col to uppercase as well
    fix_col_normalized = fix_col.upper()
    if fix_col_normalized not in df.columns:
        # Try to find the column case-insensitively
        for col in df.columns:
            if col.upper() == fix_col.upper():
                fix_col_normalized = col
                break

    expanded_route = []

    # Iterate through tokens
    i = 0
    while i < len(tokens):
        token = tokens[i].upper()

        # Check if token is an airway (exists in ENR_NM)
        # We only treat it as an airway if it's NOT the first or last item (needs start/end context)
        # AND if the previous item was a fix.
        is_airway = token in df['ENR_NM'].values
        
        if is_airway and i > 0 and i < len(tokens) - 1:
            start_fix = tokens[i-1].upper()
            end_fix = tokens[i+1].upper()
            
            # Logic to expand airway between start_fix and end_fix
            airway_df = df[df['ENR_NM'] == token].sort_values('SEQ')
            
            # Find start and end indices
            # We need to handle potential duplicates or just take the first match
            # Ideally, specific airway + fix should be unique sequence
            
            start_rows = airway_df[airway_df[fix_col_normalized] == start_fix]
            end_rows = airway_df[airway_df[fix_col_normalized] == end_fix]
            
            if start_rows.empty or end_rows.empty:
                # Cannot expand, just append the token as is (or handle error)
                # Requirement says "replace", so if we fail, maybe just keep it? 
                # Or maybe it's not an airway segment in this context?
                # For now, treat as just a point if expansion fails
                expanded_route.append(token)
                i += 1
                continue
                
            start_seq = start_rows.iloc[0]['SEQ']
            end_seq = end_rows.iloc[0]['SEQ']
            
            if start_seq < end_seq:
                # Forward direction
                segment = airway_df[(airway_df['SEQ'] > start_seq) & (airway_df['SEQ'] < end_seq)]
                # Add intermediate points
                intermediate = segment[fix_col_normalized].tolist()
                expanded_route.extend(intermediate)
            else:
                # Reverse direction
                segment = airway_df[(airway_df['SEQ'] < start_seq) & (airway_df['SEQ'] > end_seq)]
                # Sort descending for reverse
                segment = segment.sort_values('SEQ', ascending=False)
                intermediate = segment[fix_col_normalized].tolist()
                expanded_route.extend(intermediate)
                
            # We processed the airway. The loop will continue to 'end_fix' which is next.
            # Wait, if we expanded "A Y1 B", result should be "A [intermediates] B".
            # The loop processes A (added), then Y1 (expanded intermediates), then B (added).
            # "A" was added in previous iteration.
            # "Y1" adds intermediates.
            # "B" will be added in next iteration.
            i += 1
        else:
            # It's a point (or an airway that we can't expand), add it
            expanded_route.append(token)
            i += 1
            
    return expanded_route

def main():
    import warnings
    warnings.simplefilter("ignore")
    
    file_path = r'c:\Users\KAC\Desktop\test\enroute.xlsx'
    df, fix_col = load_data(file_path)
    
    test_route = "LAMEN A593 SADLI Y590 ELGEP Y722 OLMEN"
    test_route = "AGAVO G597 LANAT"
    test_route = "AGAVO Y644 REBIT"
    print(f"\n--- 테스트 실행 ---")
    print(f"입력: {test_route}")
    
    result = expand_route(df, fix_col, test_route)
    print(f"결과: {' '.join(result)}")
    print("--- 테스트 종료 ---\n")

if __name__ == "__main__":
    main()
