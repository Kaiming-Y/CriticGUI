"""Prepare an MLLM prompt; use the response as a draft, never as unreviewed GT."""
import argparse
from pathlib import Path

PROMPT = '''Draft a three-level GUI task plan for the supplied query and current screenshot.
If a demonstration video or transcript is provided, use it as additional context.
High-level (h): a major functional goal or milestone.
Low-level (l): a meaningful subtask with a specific target and desired outcome.
Atomic-level (a): one semantically minimal GUI interaction, such as clicking a
control, entering text, dragging an object, or invoking a keyboard gesture.
An atomic interaction may include several physical mouse/keyboard events.
Do not invent state that cannot be seen. Mark uncertainty with a # comment for
human review. Split steps that produce distinct state transitions. Keep all
three levels. Number h globally, l within each h, and a within each l.
Return only this format:
h0: <goal>
l0: <subtask>
a0: <atomic interaction>
a1: <next atomic interaction>

Software: {software}
User query: {query}

A human will correct the order, UI details and atomic granularity before freezing
the ground-truth plan. This response is a draft, not a verified procedure.
'''


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--query', required=True)
    p.add_argument('--software', required=True)
    p.add_argument('--output', type=Path, required=True)
    a = p.parse_args()
    a.output.parent.mkdir(parents=True, exist_ok=True)
    a.output.write_text(PROMPT.format(query=a.query, software=a.software), encoding='utf-8')
    print('Prompt saved. Submit with the initial screenshot to your MLLM, then review the draft.')

if __name__ == '__main__':
    main()
