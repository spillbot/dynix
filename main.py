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
        tags = [tag.lower() for tag in tags]  # Convert search tags to lowercase
        
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Look for YAML frontmatter
                frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                file_tags = []
                
                if frontmatter_match:
                    frontmatter = frontmatter_match.group(1)
                    # Look for tags in YAML frontmatter
                    tags_match = re.search(r'tags:\s*\[(.*?)\]', frontmatter)
                    if tags_match:
                        # Split by comma and clean each tag
                        yaml_tags = [t.strip().strip('"\'') for t in tags_match.group(1).split(',')]
                        file_tags.extend(yaml_tags)
                
                # Look for inline tags
                inline_tags = re.findall(r'#(\w+)', content)
                file_tags.extend(inline_tags)
                
                # Convert all file tags to lowercase for case-insensitive comparison
                file_tags = [tag.lower() for tag in file_tags]
                
                # Debug output
                if file_tags:
                    print(f"File: {file}")
                    print(f"Found tags: {file_tags}")
                    print(f"Searching for: {tags}")
                
                # Check if any search tag is a substring of any file tag
                # or if any file tag is a substring of any search tag
                if any(any(search_tag in file_tag or file_tag in search_tag 
                          for file_tag in file_tags) for search_tag in tags):
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

    def get_all_tags(self) -> List[str]:
        """Collect all unique tags from the vault"""
        all_tags = set()
        files = self.get_markdown_files()
        
        for file in files:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
                
                # Look for YAML frontmatter
                frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)
                if frontmatter_match:
                    frontmatter = frontmatter_match.group(1)
                    # Look for tags in YAML frontmatter
                    tags_match = re.search(r'tags:\s*\[(.*?)\]', frontmatter)
                    if tags_match:
                        # Split by comma and clean each tag
                        yaml_tags = [t.strip().strip('"\'') for t in tags_match.group(1).split(',')]
                        all_tags.update(yaml_tags)
                
                # Look for inline tags
                inline_tags = re.findall(r'#(\w+)', content)
                all_tags.update(inline_tags)
        
        return sorted(list(all_tags))

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
        instructions = "Use ↑↓ arrows to navigate, Enter to select, Ctrl+Q to exit"
        self.screen.addstr(height - 2, (width - len(instructions)) // 2, instructions)
        
        self.screen.refresh()

    def draw_search_input(self, prompt: str, is_tag_search: bool = False) -> str:
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
        
        if is_tag_search:
            # Split input into list of tags and clean them
            return [tag.strip() for tag in input_str.split(',') if tag.strip()]
        return input_str

    def draw_results(self, results: List[Tuple[str, str]], search_terms: str = None):
        self.screen.clear()
        height, width = self.screen.getmaxyx()
        current_selection = 0
        
        while True:
            self.screen.clear()
            
            # Draw title and search terms
            title = f"Found {len(results)} results"
            self.screen.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
            
            if search_terms:
                search_line = f"Search terms: {search_terms}"
                self.screen.addstr(1, (width - len(search_line)) // 2, search_line)
            
            # Draw results
            for idx, (file, content) in enumerate(results):
                if idx >= height - 3:  # Leave space for instructions and search terms
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
                    self.screen.addstr(idx + 2, 2, display, curses.A_REVERSE)
                else:
                    self.screen.addstr(idx + 2, 2, display)
            
            # Draw instructions
            instructions = "↑↓ to select, Enter to view, Esc to go back, Ctrl+q to exit"
            self.screen.addstr(height - 1, (width - len(instructions)) // 2, instructions)
            self.screen.refresh()
            
            key = self.screen.getch()
            
            # Debug: Print key code
            self.screen.addstr(height - 2, 0, f"Key code: {key}")
            self.screen.refresh()
            
            if key == curses.KEY_UP and current_selection > 0:
                current_selection -= 1
            elif key == curses.KEY_DOWN and current_selection < min(len(results) - 1, height - 4):
                current_selection += 1
            elif key == 10:  # Enter key
                self.display_content(results[current_selection])
            elif key == 27:  # Esc key
                break
            elif key == 17:  # Try Ctrl+q as 17
                raise KeyboardInterrupt

    def display_content(self, result: Tuple[str, str]):
        """Display content directly in TUI"""
        file, content = result
        height, width = self.screen.getmaxyx()
        
        # Split content into lines
        lines = content.split('\n')
        current_line = 0
        
        # Create a pad for the content
        pad = curses.newpad(len(lines) + 1, width)
        pad.scrollok(True)
        
        # Write all content to pad once
        for idx, line in enumerate(lines):
            if len(line) > width - 2:
                line = line[:width - 5] + "..."
            try:
                pad.addstr(idx, 1, line)
            except curses.error:
                pass
        
        # Draw static elements once
        title = os.path.basename(file)
        self.screen.addstr(0, (width - len(title)) // 2, title, curses.A_BOLD)
        self.screen.addstr(height - 1, (width - 40) // 2, "↑↓ to scroll, Esc to go back, Ctrl+q to exit")
        self.screen.refresh()
        
        while True:
            # Show content from pad
            try:
                pad.refresh(current_line, 0, 1, 0, height - 2, width - 1)
            except curses.error:
                pass
            
            # Handle input
            key = self.screen.getch()
            
            # Debug: Print key code
            self.screen.addstr(height - 2, 0, f"Key code: {key}")
            self.screen.refresh()
            
            if key == curses.KEY_UP and current_line > 0:
                current_line -= 1
            elif key == curses.KEY_DOWN and current_line < len(lines) - (height - 3):
                current_line += 1
            elif key == 27:  # Esc
                break
            elif key == 17:  # Try Ctrl+q as 17
                raise KeyboardInterrupt

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
                            self.draw_results(results, f"Subject: {query}")
                    elif self.menu_items[self.current_selection] == "Search by Tag(s)":
                        tags = self.draw_search_input("Enter tags (comma-separated): ", is_tag_search=True)
                        if tags:
                            results = self.search_by_tags(tags)
                            self.draw_results(results, f"Tags: {', '.join(tags)}")
                elif key == 3:  # Ctrl+C
                    break
                elif key == 17:  # Try Ctrl+q as 17
                    raise KeyboardInterrupt
        
        try:
            curses.wrapper(main)
        except KeyboardInterrupt:
            pass  # Handle Ctrl+C gracefully

if __name__ == "__main__":
    app = ObsidianTUI()
    app.run()
