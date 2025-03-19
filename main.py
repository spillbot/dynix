#!/usr/bin/env python3

import curses
import os
from datetime import datetime
import re
from typing import List, Tuple

class ObsidianTUI:
    def __init__(self):
        self.vault_path = os.path.expanduser("~/obsidian")
        self.screen = None
        self.current_selection = 0
        self.menu_items = [
            "Search by Subject",
            "Search by Tag(s)", 
            "Search by Date",
            "Exit"
        ]

    def get_markdown_files(self) -> List[str]:
        markdown_files = []
        for root, _, files in os.walk(self.vault_path):
            for file in files:
                if file.endswith(('.md', '.markdown')):
                    markdown_files.append(os.path.join(root, file))
        return markdown_files

    def search_by_subject(self, query: str) -> List[Tuple[str, str]]:
        results = []
        files = self.get_markdown_files()
        query = query.lower()
        
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Get filename without extension and path
                filename = os.path.splitext(os.path.basename(file))[0].lower()
                
                # Check first line for SUBJECT field
                first_line = content.split('\n')[0].strip()
                if first_line.startswith('SUBJECT='):
                    subject = first_line[8:].strip().lower()  # Remove 'SUBJECT=' prefix
                    if query in subject:
                        results.append((file, content))
                # Fallback to filename if no SUBJECT field or no match
                elif query in filename:
                    results.append((file, content))
                    
        return results

    def search_by_tags(self, tags: List[str]) -> List[Tuple[str, str]]:
        results = []
        files = self.get_markdown_files()
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                # Look for YAML frontmatter tags or inline tags
                found_tags = re.findall(r'tags:\s*\[(.*?)\]|#(\w+)', content)
                file_tags = []
                for tag_match in found_tags:
                    if tag_match[0]:  # YAML frontmatter
                        file_tags.extend([t.strip() for t in tag_match[0].split(',')])
                    if tag_match[1]:  # Inline tag
                        file_tags.append(tag_match[1])
                
                if any(tag.lower() in [ft.lower() for ft in file_tags] for tag in tags):
                    results.append((file, content))
        return results

    def search_by_date(self, date_str: str) -> List[Tuple[str, str]]:
        results = []
        files = self.get_markdown_files()
        try:
            search_date = datetime.strptime(date_str, "%Y-%m-%d")
            for file in files:
                file_time = datetime.fromtimestamp(os.path.getmtime(file))
                if (file_time.year == search_date.year and 
                    file_time.month == search_date.month and 
                    file_time.day == search_date.day):
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        results.append((file, content))
        except ValueError:
            pass
        return results

    def draw_menu(self):
        self.screen.clear()
        height, width = self.screen.getmaxyx()
        
        # Draw title
        title = "Obsidian Vault Search"
        self.screen.addstr(1, (width - len(title)) // 2, title, curses.A_BOLD)
        
        # Draw menu items
        for idx, item in enumerate(self.menu_items):
            y = height // 2 - len(self.menu_items) // 2 + idx
            x = (width - len(item)) // 2
            if idx == self.current_selection:
                self.screen.addstr(y, x, item, curses.A_REVERSE)
            else:
                self.screen.addstr(y, x, item)
        
        # Draw instructions
        instructions = "Use ↑↓ arrows to navigate, Enter to select"
        self.screen.addstr(height - 2, (width - len(instructions)) // 2, instructions)
        
        self.screen.refresh()

    def draw_search_input(self, prompt: str) -> str:
        self.screen.clear()
        height, width = self.screen.getmaxyx()
        
        # Draw prompt
        self.screen.addstr(1, (width - len(prompt)) // 2, prompt)
        
        # Create input box
        input_box = curses.newwin(3, width - 4, 3, 2)
        input_box.box()
        input_box.refresh()
        
        # Get input
        curses.echo()
        curses.curs_set(1)
        input_str = input_box.getstr(1, 1).decode('utf-8')
        curses.noecho()
        curses.curs_set(0)
        
        return input_str

    def draw_results(self, results: List[Tuple[str, str]]):
        self.screen.clear()
        height, width = self.screen.getmaxyx()
        current_selection = 0
        
        while True:
            self.screen.clear()
            
            # Draw title
            title = f"Found {len(results)} results"
            self.screen.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
            
            # Draw results
            for idx, (file, content) in enumerate(results):
                if idx >= height - 2:  # Leave space for instructions
                    break
                    
                # Get first line (SUBJECT) and filename
                first_line = content.split('\n')[0].strip()
                filename = os.path.basename(file)
                
                # Format display line
                if first_line.startswith('SUBJECT='):
                    display = f"{first_line[8:]} ({filename})"
                else:
                    display = filename
                    
                # Truncate if too long
                if len(display) > width - 4:
                    display = display[:width-7] + "..."
                
                # Highlight selected item
                if idx == current_selection:
                    self.screen.addstr(idx + 1, 2, display, curses.A_REVERSE)
                else:
                    self.screen.addstr(idx + 1, 2, display)
            
            # Draw instructions
            instructions = "↑↓ to select, Enter to view, Esc to go back"
            self.screen.addstr(height - 1, (width - len(instructions)) // 2, instructions)
            self.screen.refresh()
            
            key = self.screen.getch()
            
            if key == curses.KEY_UP and current_selection > 0:
                current_selection -= 1
            elif key == curses.KEY_DOWN and current_selection < min(len(results) - 1, height - 3):
                current_selection += 1
            elif key == 10:  # Enter key
                self.display_content(results[current_selection])
            elif key == 27:  # Esc key
                break

    def display_content(self, result: Tuple[str, str]):
        """Display content directly in TUI"""
        file, content = result
        self.screen.clear()
        height, width = self.screen.getmaxyx()
        
        # Split content into lines
        lines = content.split('\n')
        current_line = 0
        
        while True:
            self.screen.clear()
            
            # Draw title
            title = os.path.basename(file)
            self.screen.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
            
            # Display content
            display_height = height - 3  # Space for title and instructions
            for i in range(display_height):
                line_idx = current_line + i
                if line_idx < len(lines):
                    try:
                        line = lines[line_idx]
                        if len(line) > width - 2:
                            line = line[:width - 5] + "..."
                        self.screen.addstr(i + 1, 1, line)
                    except curses.error:
                        pass
            
            # Draw instructions
            instructions = "↑↓ to scroll, Esc to go back"
            try:
                self.screen.addstr(height - 1, (width - len(instructions)) // 2, instructions)
            except curses.error:
                pass
            
            self.screen.refresh()
            
            # Handle input
            key = self.screen.getch()
            
            if key == curses.KEY_UP and current_line > 0:
                current_line -= 1
            elif key == curses.KEY_DOWN and current_line < len(lines) - display_height:
                current_line += 1
            elif key == 27:  # Esc
                break

    def run(self):
        def main(stdscr):
            self.screen = stdscr
            curses.curs_set(0)  # Hide cursor
            
            while True:
                self.draw_menu()
                key = self.screen.getch()
                
                if key == curses.KEY_UP and self.current_selection > 0:
                    self.current_selection -= 1
                elif key == curses.KEY_DOWN and self.current_selection < len(self.menu_items) - 1:
                    self.current_selection += 1
                elif key == 10:  # Enter key
                    if self.menu_items[self.current_selection] == "Exit":
                        break
                    elif self.menu_items[self.current_selection] == "Search by Subject":
                        query = self.draw_search_input("Enter search term: ")
                        if query:
                            results = self.search_by_subject(query)
                            self.draw_results(results)
                elif key == 3:  # Ctrl+C
                    break
        
        try:
            curses.wrapper(main)
        except KeyboardInterrupt:
            pass  # Handle Ctrl+C gracefully

if __name__ == "__main__":
    app = ObsidianTUI()
    app.run()
