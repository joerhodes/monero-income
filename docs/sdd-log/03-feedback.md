# Feadback

## My view

Building the list of behaviors took several rounds of review and became a struggle to understand when to add the details to this behavior list instead of addressing later in to the process.  It also seem to chew up a lot of time for such a small application.

## Claude conversation

The xmr-income-report is small but it took some time to get the behavior list complete.  For me it was painful enough that I'm starting to have doubts that SDD is the solutions to the problems we discussed related to Agentic Editors and the workflow change they induce.   I can see myself continuing to feed Claude small tasks, one at a time, instead of creating a full spec.   But I can admin I'm going from a bottom-up developer view.   So I'm hopeful to see something that will change my mind.


That's a fair reaction, and it's worth taking seriously instead of pushing through. A few things to separate out.

**Much of the pain wasn't SDD overhead.** UTC vs. local, round once, "no value, not zero": you'd already made those decisions, but they lived implicitly in your schema and code, reached gradually over several versions. The inventory made you state them all at once. A rewrite is the worst case for how this *feels*: you already know every answer, so writing them down looks like pure cost with no discovery. On a new project, the same questions come up anyway. You'd just meet them in the middle of implementation instead. I also pushed for more precision than a lighter process would have needed, so some of the friction came from me, not the method.

**Small-task prompting has a spec too. It's just in your head.** Each prompt carries part of it, and the agent re-infers the rest every time. That works well when you're paying attention to every step and the whole tool fits in your head, which is true for this project. It fails quietly when a prompt doesn't happen to restate a rule. "Add a weekly total" is exactly where an agent might sum rounded values or treat missing as zero. The inventory is the context you'd otherwise re-explain, or forget to, across dozens of prompts.

**Your skepticism may also just be correct for this scale.** For a small solo tool you understand completely, a constitution plus a good `CLAUDE.md` plus small, focused tasks may capture most of the value at a fraction of the ceremony. SDD's case gets stronger when the agent works in larger chunks without you, when more than one person or agent touches the code, or when you come back after months and the spec is faster to read than the code. If that's where you land, it's a legitimate result of the experiment. As a portfolio finding, "here's where SDD paid off and where it didn't" is more credible than uncritical enthusiasm.

**What could change your mind is testable, so define the test now.** Specs 001 and 002 are mostly rewrite tax. The evidence comes later:
- **Implement:** how much correction does a spec-driven implementation need compared with what you remember of building v0.1–v0.2 task by task?
- **Enhancements:** when finalization and row limits come up as natural enhancements, is adding them to a spec'd codebase faster and less error-prone, because the rules are already written down?
- **Return after a gap:** after a few weeks away, do the specs get you back up to speed faster than the code does?

Put those three questions in the log now, alongside your doubts. Then the experiment has a real hypothesis, and whichever way it comes out, you'll have evidence instead of a feeling.
