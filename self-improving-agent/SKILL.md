---
name: self-improving-agent
description: A self-improving agent system that learns from interactions, analyzes performance, and continuously optimizes its behavior. Use when the agent needs to (1) Reflect on past interactions and identify improvement opportunities, (2) Update its own memory and knowledge base based on experience, (3) Optimize skill usage patterns and workflows, (4) Track performance metrics and learning progress, (5) Adapt behavior based on user feedback and preferences.
---

# Self-Improving Agent

## Overview

This skill enables the agent to learn from experience, reflect on its performance, and continuously improve its capabilities. It provides a structured approach to self-reflection, memory management, and behavioral optimization.

## Core Capabilities

### 1. Reflection & Learning

After completing tasks or when explicitly requested, the agent can:
- Analyze what worked well and what didn't
- Identify patterns in successful vs. unsuccessful interactions
- Extract lessons learned from mistakes
- Document insights for future reference

### 2. Memory Management

The agent maintains and updates:
- **Interaction history** - Key conversations and their outcomes
- **User preferences** - Communication style, priorities, pet peeves
- **Performance metrics** - Success rates, response times, user satisfaction
- **Knowledge gaps** - Areas where the agent needs improvement

### 3. Skill Optimization

The agent can:
- Track which skills are used most effectively
- Identify underutilized or misused skills
- Suggest improvements to skill documentation
- Adapt skill selection based on context

### 4. Behavioral Adaptation

Based on accumulated learning, the agent can:
- Adjust communication style to match user preferences
- Proactively offer help based on patterns
- Anticipate needs from historical context
- Refine decision-making heuristics

## Workflow

### Learning Cycle

```
Experience → Reflect → Identify → Update → Apply
```

1. **Experience** - Complete a task or interaction
2. **Reflect** - Analyze the interaction for learning opportunities
3. **Identify** - Pinpoint specific improvements or insights
4. **Update** - Modify memory files with new learnings
5. **Apply** - Use updated knowledge in future interactions

### When to Trigger Self-Improvement

- After completing complex multi-step tasks
- When receiving explicit feedback (positive or negative)
- When noticing recurring patterns in user requests
- Periodically during low-activity periods (heartbeat)
- When explicitly asked by the user

## Memory Structure

### Daily Notes (`memory/YYYY-MM-DD.md`)

Raw logs of daily interactions:
- Key conversations
- Decisions made
- Mistakes and corrections
- User feedback

### Long-term Memory (`MEMORY.md`)

Curated wisdom distilled from daily notes:
- Enduring user preferences
- Proven strategies and patterns
- Lessons learned
- Knowledge gaps to address

### Performance Tracking (`memory/performance.json`)

Structured metrics:
```json
{
  "skill_usage": {
    "skill-name": {
      "invocations": 10,
      "success_rate": 0.9,
      "avg_response_time": 5.2
    }
  },
  "user_feedback": {
    "positive": 15,
    "neutral": 3,
    "negative": 1
  },
  "learning_moments": [
    {
      "date": "2024-01-15",
      "insight": "User prefers concise responses",
      "source": "explicit_feedback"
    }
  ]
}
```

## Usage Patterns

### Pattern 1: Post-Task Reflection

After completing a task, automatically reflect:

```markdown
Task completed: [description]

Reflection:
- What went well: [observations]
- What could improve: [observations]
- User feedback: [if any]
- Action items: [updates to make]
```

### Pattern 2: Periodic Review

During heartbeat or scheduled review:

1. Read recent daily notes
2. Identify recurring themes
3. Update MEMORY.md with distilled insights
4. Archive or clean up old daily notes
5. Update performance metrics

### Pattern 3: Explicit Learning Request

When user says "learn from this" or "remember that":

1. Capture the specific learning
2. Categorize it (preference, lesson, fact, etc.)
3. Update appropriate memory file
4. Acknowledge the learning

## Best Practices

### What to Remember

- **User preferences** - Communication style, format preferences, priorities
- **Successful patterns** - Approaches that worked well
- **Mistakes** - Errors made and how they were corrected
- **Context** - Project details, ongoing work, important dates

### What NOT to Remember

- Sensitive personal information (passwords, secrets)
- Temporary or trivial details
- Speculative or uncertain information
- Information that violates privacy

### Memory Maintenance

- Review MEMORY.md weekly for outdated information
- Consolidate daily notes into long-term memory regularly
- Remove or archive information that's no longer relevant
- Keep MEMORY.md focused on actionable insights

## Resources

### scripts/

- `reflect.py` - Analyze recent interactions and generate reflections
- `update_memory.py` - Update memory files with new learnings
- `track_performance.py` - Log and analyze performance metrics

### references/

- `reflection-prompts.md` - Structured prompts for different types of reflection
- `memory-templates.md` - Templates for consistent memory documentation
- `learning-patterns.md` - Common learning patterns and how to apply them
