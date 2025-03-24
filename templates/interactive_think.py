TRUNCATE_SEQS = [
    'Wait', 'wait',
    'Alternatively', 'alternatively',
]

FEEDBACK_MIND_CONTENT = {
"Right": \
"""
<thinking_feedback>
Since my current reasoning is in the right direction, I must keep my previous reasoning and continue to delve a deeper reasoning to obtain the fianl answer.
<\\thinking feedback>
My continued reasoning is as follows:
""",
"Wrong": \
"""
<thinking_feedback>
Since my current reasoning is in the wrong direction, I must abandon my previous reasoning and start over to find the correct answer.
<\\thinking feedback>
My continued reasoning is as follows:
""",
"WrongSuggest": \
"""
<thinking_feedback>
Since my current reasoning is in the wrong direction, I must abandon my previous reasoning and start over to find the correct answer.
Here is a hint: {hint}
<\\thinking feedback>
My continued reasoning is as follows:
"""
}