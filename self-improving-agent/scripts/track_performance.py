#!/usr/bin/env python3
"""
Performance Tracking Script - Log and analyze agent performance metrics

Usage:
    track_performance.py --skill <name> --outcome <success|failure>
    track_performance.py --feedback <positive|neutral|negative>
    track_performance.py --report

Examples:
    track_performance.py --skill feishu-doc --outcome success
    track_performance.py --feedback positive
    track_performance.py --report
"""

import argparse
import json
from datetime import datetime
from pathlib import Path

PERFORMANCE_FILE = 'memory/performance.json'


def ensure_performance_file():
    """Ensure performance tracking file exists."""
    perf_path = Path(PERFORMANCE_FILE)
    if not perf_path.parent.exists():
        perf_path.parent.mkdir(parents=True, exist_ok=True)
    
    if not perf_path.exists():
        default_data = {
            'skill_usage': {},
            'user_feedback': {'positive': 0, 'neutral': 0, 'negative': 0},
            'learning_moments': [],
            'metrics_history': []
        }
        perf_path.write_text(json.dumps(default_data, indent=2), encoding='utf-8')
    
    return perf_path


def load_performance_data():
    """Load performance data from file."""
    perf_path = ensure_performance_file()
    return json.loads(perf_path.read_text(encoding='utf-8'))


def save_performance_data(data):
    """Save performance data to file."""
    perf_path = ensure_performance_file()
    perf_path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')


def track_skill_usage(skill_name, outcome):
    """Track skill usage and outcome."""
    data = load_performance_data()
    
    if skill_name not in data['skill_usage']:
        data['skill_usage'][skill_name] = {
            'invocations': 0,
            'successes': 0,
            'failures': 0,
            'success_rate': 0.0
        }
    
    skill_data = data['skill_usage'][skill_name]
    skill_data['invocations'] += 1
    
    if outcome == 'success':
        skill_data['successes'] += 1
    else:
        skill_data['failures'] += 1
    
    # Calculate success rate
    total = skill_data['successes'] + skill_data['failures']
    skill_data['success_rate'] = skill_data['successes'] / total if total > 0 else 0.0
    
    # Add timestamp
    skill_data['last_used'] = datetime.now().isoformat()
    
    save_performance_data(data)
    print(f"[OK] Tracked {outcome} for skill: {skill_name}")


def track_feedback(feedback_type):
    """Track user feedback."""
    data = load_performance_data()
    
    if feedback_type in data['user_feedback']:
        data['user_feedback'][feedback_type] += 1
    
    save_performance_data(data)
    print(f"[OK] Tracked {feedback_type} feedback")


def add_learning_moment(insight, source='reflection'):
    """Add a learning moment."""
    data = load_performance_data()
    
    learning_moment = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'insight': insight,
        'source': source
    }
    
    data['learning_moments'].append(learning_moment)
    save_performance_data(data)
    print(f"[OK] Added learning moment")


def generate_report():
    """Generate performance report."""
    data = load_performance_data()
    
    print("=" * 50)
    print("PERFORMANCE REPORT")
    print("=" * 50)
    
    # Skill usage
    print("\n📊 Skill Usage:")
    if data['skill_usage']:
        for skill, stats in sorted(data['skill_usage'].items()):
            success_rate = stats['success_rate'] * 100
            print(f"  {skill}:")
            print(f"    Invocations: {stats['invocations']}")
            print(f"    Success Rate: {success_rate:.1f}%")
    else:
        print("  No skill usage data yet")
    
    # User feedback
    print("\n👤 User Feedback:")
    feedback = data['user_feedback']
    total = sum(feedback.values())
    if total > 0:
        for fb_type, count in feedback.items():
            percentage = (count / total) * 100
            print(f"  {fb_type.capitalize()}: {count} ({percentage:.1f}%)")
    else:
        print("  No feedback recorded yet")
    
    # Learning moments
    print("\n🧠 Recent Learning Moments:")
    if data['learning_moments']:
        for moment in data['learning_moments'][-5:]:  # Last 5
            print(f"  [{moment['date']}] {moment['insight'][:60]}...")
    else:
        print("  No learning moments recorded yet")
    
    print("\n" + "=" * 50)


def main():
    parser = argparse.ArgumentParser(description='Track agent performance')
    parser.add_argument('--skill', help='Skill name')
    parser.add_argument('--outcome', choices=['success', 'failure'],
                        help='Outcome of skill usage')
    parser.add_argument('--feedback', choices=['positive', 'neutral', 'negative'],
                        help='User feedback type')
    parser.add_argument('--learning', help='Add a learning moment')
    parser.add_argument('--report', action='store_true',
                        help='Generate performance report')
    
    args = parser.parse_args()
    
    if args.report:
        generate_report()
    elif args.skill and args.outcome:
        track_skill_usage(args.skill, args.outcome)
    elif args.feedback:
        track_feedback(args.feedback)
    elif args.learning:
        add_learning_moment(args.learning)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
