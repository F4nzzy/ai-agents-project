# Decisions 

## Week 1

**Run conditions.** Everything below was produced on:

- machine: DELL XPS 13 9320, 12th Gen Intel i7-1260P (16), 32 GB
- model: qwen3:4b-instruct
- served by: Ollama, one request at a time, locally
- date: 2026-09-16

Every number in this file is meaningless without those four lines, so they
are stated once here and referred to rather than repeated.

### 1. Machine and model set

I am running the required plus optional model set.

### 2. The first call

| | |
| finish reason | stop |
| prompt tokens | 24 |
| completion tokens | 45 |
| elapsed | 12.34496806000061 |

One sentence on the finish reason: what my program would do differently if
it came back as a truncation rather than a normal stop.

If the finish reason was length instead of stop then that would mean that it ran out of tokens, the response would be cut off mid-generation.

### 3. Variance

| cell | distinct (recording) | distinct (mine) | median latency |
| closed_short, t=0.0 | 1/12 | 1/6 | 0.38 |
| closed_short, t=1.0 | 1/12 | 1/6 | 0.34 |
| open_list, t=0.0 | 1/12 | 1/6 | 4.86 |
| open_list, t=1.0 | 11/12 | 6/6 | 4.16 |

Which cell still returns a single answer at temperature 1.0, and why that
one:

The cell that returns on single distinct answer is closed_short|t10. The reason it gives this result is because the question, "What is the capital of Luxembourg? Answer in one word." will give the same answer each time.

Which cells a test asserting exact string equality would pass on, and what
that tells me about testing this system:

It would pass for closed_short|t00, closed_short|t10 and open_list|t00, and would fail on open_list|t10. This tells us that the testing system is insufficient because exact-match testing only works for when the output is almost always the same. It fails if the outcome can differ

**The sentence that carries into week 10.** [One sentence about when you can
and cannot rely on repeating an output. Week 10 will ask you to find this
again. It should not say "the model is random", because your own table shows
otherwise in most cells.]

You can rely on repeating an output either when the temperature is 0, or if the question has a response that is always the same, however if the question is openended and has many possible responses or if the temperature is more than 0, then repetition cannot be expected. 

### 4. The cold start

- cold call: 29.94 s
- warm call: 24.01 s
- ratio: 1.25

What this implies for a system that uses more than one model, and what I
will do about it:

This implies a penalty when switching models, therefore it is optimal to keep the necessary models warm. 

### 5. Cost, estimated

A 200-case golden set, at the token cost of my long case:

| | one run | nightly for the semester |
| small tier | 0.03 | 3.28 |
| large tier | 2.49 | 244.14 |

Estimates against the price list dated 2026-08-10, not
measurements. Running locally, my actual monetary cost was zero.

Which tier I would run nightly, which I would run before a release, and why
not the same one for both:

Nightly, I would run the 'small' tier as it is cheaper, however before release I would run the 'large' tier for better results. I wouldn't do the same for both because if you run 'large' nightly it will cost over 70x more and if you run 'small' before release it may be inaccurate. 

### Deferred

Nothing deferred. 
