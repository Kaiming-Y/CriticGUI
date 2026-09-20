# Agent exploration + human demonstration

Use the [WorldGUI agent](https://github.com/showlab/WorldGUI) for the Plan-Act-Critic exploration branch. Follow that repository's environment and execution instructions. CriticGUI does not claim a new independent implementation of that agent.

Agent exploration yields naturally occurring decisions and failures. Human demonstrations reach difficult states the agent may not reliably produce; manually perturbed variants add controlled negative contrasts. Both are useful sources of critic examples.

## Bringing sources together

For an agent trajectory, retain the actual instruction/context, executed action, visual observations before and after it, and available video. Have the outcome and reason reviewed against that evidence. Preserve `source: agent_exploration`, the agent/model version, task and trajectory IDs.

An adapter is still needed to map your chosen WorldGUI log version to an evaluation schema. This release exports the human branch only; it does not provide an automatic agent-log importer. Do not invent an atomic instruction retrospectively if the trace does not support that segmentation—review and document the mapping.

Keep task families and paired variants together when splitting data. Report collection source and difficulty separately when analyzing critic performance; human collection extends coverage but does not itself guarantee a balanced or unbiased benchmark.
