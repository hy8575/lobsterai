#!/usr/bin/env python3
"""
Reflection Script - Analyze recent interactions and generate insights

Usage:
    reflect.py --memory-file <path> [--days <n>]
    reflect.py --interaction "<description>" --outcome "<result>"

Examples:
    reflect.py --memory-file memory/2024-03-14.md --days 1
    reflect.py --interaction "Helped user debug Python script" --outcome "Success after 3 attempts"
"""

import argparse
import json
import re
from datetime import datetime, timedelta
from pathlib import Path


def parse_memory_file(filepath):
    """Parse a memory file and extract key interactions."""
    content = Path(filepath).read_text(encoding='utf-8')
    
    # Look for patterns like "Task:", "Decision:", "Mistake:", "Lesson:"
    patterns = {
        'tasks': r'(?:Task|任务)[：:](.+?)(?=\n\n|\n(?:Task|Decision|Mistake|Lesson)|$)',
        'decisions': r'(?:Decision|决定)[：:](.+?)(?=\n\n|\n(?:Task|Decision|Mistake|Lesson)|$)',
        'mistakes': r'(?:Mistake|错误)[：:](.+?)(?=\n\n|\n(?:Task|Decision|Mistake|Lesson)|$)',
        'lessons': r'(?:Lesson|教训|经验)[：:](.+?)(?=\n\n|\n(?:Task|Decision|Mistake|Lesson)|$)',
    }
    
    results = {}
    for key, pattern in patterns.items():
        matches = re.findall(pattern, content, re.DOTALL | re.IGNORECASE)
        results[key] = [m.strip() for m in matches if m.strip()]
    
    return results


def generate_reflection(interactions):
    """Generate reflection insights from parsed interactions."""
    reflection = {
        'timestamp': datetime.now().isoformat(),
        'summary': {},
        'insights': [],
        'action_items': []
    }
    
    # Count types
    reflection['summary'] = {
        'tasks_completed': len(interactions.get('tasks', [])),
        'decisions_made': len(interactions.get('decisions', [])),
        'mistakes_made': len(interactions.get('mistakes', [])),
        'lessons_learned': len(interactions.get('lessons', []))
    }
    
    # Generate insights from mistakes
    for mistake in interactions.get('mistakes', []):
        reflection['insights'].append({
            'type': 'improvement',
            'source': 'mistake',
            'content': f"Need to improve: {mistake[:100]}..."
        })
    
    # Generate insights from lessons
    for lesson in interactions.get('lessons', []):
        reflection['insights'].append({
            'type': 'learning',
            'source': 'lesson',
            'content': lesson[:150]
        })
    
    # Generate action items
    if interactions.get('mistakes'):
        reflection['action_items'].append("Review and document common error patterns")
    if interactions.get('lessons'):
        reflection['action_items'].append("Update MEMORY.md with new lessons learned")
    
    return reflection


def reflect_on_memory_files(days=1, memory_dir='memory'):
    """Reflect on memory files from the last N days."""
    memory_path = Path(memory_dir)
    if not memory_path.exists():
        print(f"[WARN] Memory directory not found: {memory_dir}")
        return None
    
    cutoff_date = datetime.now() - timedelta(days=days)
    all_interactions = {
        'tasks': [],
        'decisions': [],
        'mistakes': [],
        'lessons': []
    }
    
    # Find and parse memory files
    for file_path in memory_path.glob('*.md'):
        # Extract date from filename (YYYY-MM-DD.md)
        try:
            file_date = datetime.strptime(file_path.stem, '%Y-%m-%d')
            if file_date >= cutoff_date:
                interactions = parse_memory_file(file_path)
                for key in all_interactions:
                    all_interactions[key].extend(interactions.get(key, []))
        except ValueError:
            continue  # Not a dated memory file
    
    return generate_reflection(all_interactions)


def quick_reflect(interaction, outcome):
    """Generate a quick reflection for a single interaction."""
    reflection = {
        'timestamp': datetime.now().isoformat(),
        'interaction': interaction,
        'outcome': outcome,
        'insights': [],
        'action_items': []
    }
    
    # Simple heuristic analysis
    if 'success' in outcome.lower() or '完成' in outcome:
        reflection['insights'].append({
            'type': 'success_pattern',
            'content': f"Successful approach: {interaction[:100]}"
        })
    elif 'fail' in outcome.lower() or 'error' in outcome.lower() or '错误' in outcome:
        reflection['insights'].append({
            'type': 'improvement_needed',
            'content': f"Needs improvement: {interaction[:100]}"
        })
        reflection['action_items'].append("Document this error pattern for future reference")
    
    return reflection


def main():
    parser = argparse.ArgumentParser(description='Generate reflection insights')
    parser.add_argument('--memory-file', help='Path to memory file to analyze')
    parser.add_argument('--days', type=int, default=1, help='Number of days to look back')
    parser.add_argument('--interaction', help='Description of an interaction')
    parser.add_argument('--outcome', help='Outcome of the interaction')
    parser.add_argument('--output', '-o', help='Output file for reflection (JSON)')
    
    args = parser.parse_args()
    
    if args.memory_file:
        # Analyze specific memory file
        interactions = parse_memory_file(args.memory_file)
        reflection = generate_reflection(interactions)
    elif args.interaction and args.outcome:
        # Quick reflection on single interaction
        reflection = quick_reflect(args.interaction, args.outcome)
    else:
        # Reflect on recent memory files
        reflection = reflect_on_memory_files(args.days)
    
    if reflection:
        output = json.dumps(reflection, indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(output, encoding='utf-8')
            print(f"[OK] Reflection saved to {args.output}")
        else:
            print(output)
    else:
        print("[WARN] No reflection generated")


if __name__ == '__main__':
    main()
