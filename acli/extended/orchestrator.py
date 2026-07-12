"""Planner-coder-tester-reviewer multi-agent MVP."""
ROLES=[
 ('planner','Create a concrete implementation plan. Do not edit files yet.'),
 ('coder','Implement the plan using available tools. Keep changes focused.'),
 ('tester','Run relevant tests and diagnose any failures. Fix simple failures.'),
 ('reviewer','Review the final diff for correctness, security, and maintainability. State remaining risks.'),
]

def run_team(engine, task: str) -> str:
    outputs=[]
    for role,instruction in ROLES:
        prompt='You are the '+role.upper()+' agent. '+instruction+'\n\nShared task: '+task+'\nSummarize your result for the next agent.'
        outputs.append('['+role+']\n'+engine.send(prompt))
    return '\n\n'.join(outputs)
