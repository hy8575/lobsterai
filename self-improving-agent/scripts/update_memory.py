#!/usr/bin/env python3
"""
Memory Update Script - Update memory files with new learnings

Usage:
    update_memory.py --type <preference|lesson|fact> --content "<text>"
    update_memory.py --from-reflection <reflection.json>

Examples:
    update_memory.py --type preference --content "User prefers concise responses"
    update_memory.py --type lesson --content "Always verify file existence before reading"
    update_memory.py --from-reflection reflection.json
"""

import argparse
import json
import re
from datetime import datetime
from pathlib import Path

MEMORY_FILE = 'MEMORY.md'
DAILY_DIR = 'memory'


def ensure_daily_note():
    """Ensure today's daily note exists."""
    today = datetime.now().strftime('%Y-%m-%d')
    daily_path = Path(DAILY_DIR) / f'{today}.md'
    
    if not daily_path.parent.exists():
        daily_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not daily_path.exists():
        daily_path.write_text(f'# {today}\n\n', encoding='utf-8')
    
    return daily_path


def ensure_memory_file():
    """Ensure main MEMORY.md exists."""
    memory_path = Path(MEMORY_FILE)
    if not memory_path.exists():
        memory_path.write_text('# Long-term Memory\n\n', encoding='utf-8')
    return memory_path


def update_daily_note(content, category='Note'):
    """Add an entry to today's daily note."""
    daily_path = ensure_daily_note()
    
    timestamp = datetime.now().strftime('%H:%M')
    entry = f"\n## {timestamp} - {category}\n\n{content}\n"
    
    with open(daily_path, 'a', encoding='utf-8') as f:
        f.write(entry)
    
    return daily_path


def update_long_term_memory(content, section=None):
    """Update MEMORY.md with curated content."""
    memory_path = ensure_memory_file()
    memory_content = memory_path.read_text(encoding='utf-8')
    
    # Add timestamp
    today = datetime.now().strftime('%Y-%m-%d')
    entry = f"\n- [{today}] {content}\n"
    
    if section and f'## {section}' in memory_content:
        # Append to existing section
        pattern = f'(## {section}.*?)(\n## |\Z)'
        match = re.search(pattern, memory_content, re.DOTALL)
        if match:
            insert_pos = match.end(1)
            memory_content = memory_content[:insert_pos] + entry + memory_content[insert_pos:]
    else:
        # Append to end
        memory_content += entry
    
    memory_path.write_text(memory_content, encoding='utf-8')
    return memory_path


def process_reflection(reflection_file):
    """Process a reflection JSON file and update memory."""
    reflection = json.loads(Path(reflection_file).read_text(encoding='utf-8'))
    
    updated_files = []
    
    # Update daily note with reflection summary
    if 'insights' in reflection:
        insights_text = '\n'.join([f"- {i['content']}" for i in reflection['insights']])
        daily_path = update_daily_note(insights_text, 'Reflection')
        updated_files.append(daily_path)
    
    # Update long-term memory with key learnings
    if 'insights' in reflection:
        for insight in reflection['insights']:
            if insight['type'] == 'learning':
                memory_path = update_long_term_memory(
                    insight['content'], 
                    section='Lessons Learned'
                )
                if memory_path not in updated_files:
                    updated_files.append(memory_path)
    
    return updated_files


def main():
    parser = argparse.ArgumentParser(description='Update memory files')
    parser.add_argument('--type', choices=['preference', 'lesson', 'fact', 'note'],
                        help='Type of memory to store')
    parser.add_argument('--content', help='Content to store')
    parser.add_argument('--from-reflection', help='Process reflection JSON file')
    parser.add_argument('--long-term', action='store_true',
                        help='Store in long-term memory (MEMORY.md)')
    parser.add_argument('--section', help='Section in long-term memory')
    
    args = parser.parse_args()
    
    if args.from_reflection:
        updated = process_reflection(args.from_reflection)
        for f in updated:
            print(f"[OK] Updated: {f}")
    elif args.type and args.content:
        if args.long_term:
            path = update_long_term_memory(args.content, args.section)
            print(f"[OK] Added to long-term memory: {path}")
        else:
            category = args.type.capitalize()
            path = update_daily_note(args.content, category)
            print(f"[OK] Added to daily note: {path}")
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
