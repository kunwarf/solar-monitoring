#!/usr/bin/env python3
"""
Quick SQLite database access script using Python (no sqlite3 CLI needed)
Usage:
    python access_db.py                    # Show recent records
    python access_db.py "SELECT COUNT(*) FROM energy_samples"  # Run custom query
    python access_db.py --interactive       # Interactive mode
"""

import sqlite3
import sys
import os
from pathlib import Path

def get_db_path():
    """Get the database path from DataLogger or default location"""
    try:
        from solarhub.logging.logger import DataLogger
        logger = DataLogger()
        return logger.path
    except Exception:
        # Fallback to default location
        home = Path.home()
        return str(home / ".solarhub" / "solarhub.db")

def format_row(row, columns):
    """Format a row for display"""
    return dict(zip(columns, row))

def print_table(rows, columns):
    """Print results in a table format"""
    if not rows:
        print("No results")
        return
    
    # Calculate column widths
    col_widths = {}
    for col in columns:
        col_widths[col] = max(
            len(str(col)),
            max(len(str(row[i])) for row in rows for i, c in enumerate(columns) if c == col)
        )
    
    # Print header
    header = " | ".join(str(col).ljust(col_widths[col]) for col in columns)
    print(header)
    print("-" * len(header))
    
    # Print rows
    for row in rows:
        print(" | ".join(str(row[i]).ljust(col_widths[col]) for i, col in enumerate(columns)))

def main():
    db_path = get_db_path()
    
    if not os.path.exists(db_path):
        print(f"Error: Database not found at {db_path}")
        print("\nThe database will be created automatically when you run the solar monitoring system.")
        sys.exit(1)
    
    # Interactive mode
    if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
        print(f"SQLite Database: {db_path}")
        print("Type SQL queries (or 'quit' to exit, 'help' for commands)")
        print("-" * 60)
        
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        
        while True:
            try:
                query = input("\nsqlite> ").strip()
                
                if not query:
                    continue
                
                if query.lower() in ['quit', 'exit', 'q']:
                    break
                
                if query.lower() == 'help':
                    print("\nCommands:")
                    print("  .tables          - Show all tables")
                    print("  .schema [table]  - Show table schema")
                    print("  .count [table]   - Count records in table")
                    print("  .latest [table]  - Show latest record")
                    print("  quit/exit        - Exit")
                    continue
                
                if query.startswith('.tables'):
                    cur = con.cursor()
                    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    tables = [row[0] for row in cur.fetchall()]
                    print("\nTables:", ", ".join(tables))
                    continue
                
                if query.startswith('.schema'):
                    table = query.split()[1] if len(query.split()) > 1 else None
                    cur = con.cursor()
                    if table:
                        cur.execute(f"SELECT sql FROM sqlite_master WHERE type='table' AND name='{table}'")
                    else:
                        cur.execute("SELECT sql FROM sqlite_master WHERE type='table'")
                    for row in cur.fetchall():
                        print(row[0])
                    continue
                
                if query.startswith('.count'):
                    table = query.split()[1] if len(query.split()) > 1 else 'energy_samples'
                    cur = con.cursor()
                    cur.execute(f"SELECT COUNT(*) FROM {table}")
                    print(f"\nTotal records in {table}: {cur.fetchone()[0]}")
                    continue
                
                if query.startswith('.latest'):
                    table = query.split()[1] if len(query.split()) > 1 else 'energy_samples'
                    cur = con.cursor()
                    cur.execute(f"SELECT * FROM {table} ORDER BY ts DESC LIMIT 1")
                    row = cur.fetchone()
                    if row:
                        print("\nLatest record:")
                        for key in row.keys():
                            print(f"  {key}: {row[key]}")
                    else:
                        print("No records found")
                    continue
                
                # Execute SQL query
                cur = con.cursor()
                cur.execute(query)
                
                # Get column names
                columns = [description[0] for description in cur.description] if cur.description else []
                rows = cur.fetchall()
                
                if rows:
                    if len(rows) == 1 and len(columns) == 1:
                        # Single value result
                        print(f"\nResult: {rows[0][0]}")
                    else:
                        # Multiple rows
                        print(f"\n{len(rows)} row(s):")
                        print_table(rows, columns)
                else:
                    print("Query executed successfully (no results)")
                    
            except KeyboardInterrupt:
                print("\nExiting...")
                break
            except Exception as e:
                print(f"Error: {e}")
        
        con.close()
        return
    
    # Single query mode
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        # Default: show recent records
        query = "SELECT * FROM energy_samples ORDER BY ts DESC LIMIT 10"
    
    try:
        con = sqlite3.connect(db_path)
        con.row_factory = sqlite3.Row
        cur = con.cursor()
        cur.execute(query)
        
        columns = [description[0] for description in cur.description] if cur.description else []
        rows = cur.fetchall()
        
        if rows:
            if len(rows) == 1 and len(columns) == 1:
                print(rows[0][0])
            else:
                print_table(rows, columns)
        else:
            print("No results")
        
        con.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()

