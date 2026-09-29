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



## Week 2

**Run conditions.** model: qwen3:4b-instruct | temperature: 0.0 | prompt version: week02-zero-shot-v1 | served locally | date: 2026-09-23 | scored on: my own machine

### 1. The output contract

The conventions I chose, and why:

- due_date, when the message states no date: null
- due_date, when the message states only a relative expression: null
- quote, and what "verbatim" means in my scorer: exact substring match
- what my scorer does with a record that failed validation: counts it as wrong on all fields. 

A scorer that skips the records it could not parse reports a number that improves as the model gets worse, because a model that fails validations more often will have less records left to be wrong with. 

### 2. Zero-shot, per field

| field | correct | of |
| category | 7 | 10 |
| urgency | 10 | 10 |
| due_date | 6 | 10 |
| quote | 9 | 10 |
| invalid records | 0 | 10 |

My prediction, written before block 3: examples will help most on due date because the model invents a date for when the gold answer is None.

### 3. Few-shot

Examples chosen, and the job each one does:

| example | why it is in the block | field it should move |
| 1 | should be categorised as 'access' instead of hardware | category |
| 4 | mentions 'next week' but the due date is still None | due_date |
| 3 | to extract the date from a given date instead of always using None | None |
| 2 | to reinforce the multi-language accepted inputs | None |

| field | zero-shot | few-shot | move |
| category | 7 | 7 | 0 |
| urgency | 10 | 10 | 0 |
| due_date | 6 | 9 | +3 |
| quote | 9 | 10 | +1 |

### 4. What got worse

Nothing got worse. We checked by analyzing the 'move' column, where all values either showed a neutral move (+0) or a positive change (+1, +3), showing that the results either stayed the same or got better. 

For req-08, the failure changed from 'access' to 'facilities' when it expects 'hardware'

### 5. What the examples cost

- extra input tokens per call: 306
- per thousand calls: 306000
- estimated euros per thousand calls on the small tier: 0.06, against the
  price list dated 2026-08-10. Estimate, not a measurement.

### 6. Ship it or not

I would ship the few-shot variant. This is because the due_date was improved by +3 and the quote was improved by +1 and everything else stayed neutral. This shows that nothing got worse, only better or the same. The only thing worth noting is that whilst the count didnt change, the failure changed shape for REQ-08. REQ-08 went from "access"
to "facilities", which are both wrong. 

Ten records is not enough to be confident that few-shot is 100% better than zero-shot, and if a larger gold set showed these results to be an anomaly then this would change my mind about which is better. 

### Sensitivity variant

Variant assigned: [ ]. What I changed: [ ]. What moved: [ ].

[If nothing moved, say so. A knob that changes nothing measurable is a real
result, and it tells the room which knobs are worth arguing about.]

### The gold set

Ten cases written to `artifacts/goldset.json`, tagged by language.

One thing my scorer cannot currently detect:

[This is the most valuable line on the page. An example: "our scorer cannot
tell a correctly formatted date that is simply the wrong date from a
correctly extracted one, because it only compares strings."]

### Deferred

nothing deferred




## Week 3

**Run conditions.** classifier model: [ ] | answering model: [ ] |
temperature: 0.0 | served locally | date: [YYYY-MM-DD] | scored on: [the
recording / my own machine]

### 1. The five route definitions

| route | definition, one sentence, in terms of what the help desk must do |
| request | |
| info | |
| status | |
| complaint | |
| other | |

My convention for the four ambiguous queries:

[Two defensible conventions exist. Neither is discoverable from the data.
What matters is that yours was written down before you measured, not which
one you picked.]

Do my definitions match the ones in `queries.py`? [yes / no, and if no, what
that does to my accuracy number]

### 2. The policy layer

Before choosing a threshold, the confidence values I saw were: min [ ],
max [ ], [ ] distinct values across 24 queries.

- confidence floor: [ ], because [ ]
- evidence check: [what I do when the span is not in the message], because [ ]
- safe default: [ ], because that specialist [ ]

How often each check fired: below_threshold [ ], evidence_not_verbatim [ ],
invalid_decision [ ].

[If a check fired zero times, say what that tells you. A threshold that
never fires is either a very good classifier or a useless signal, and the
confidence distribution above tells you which.]

### 3. Route accuracy

| route | correct | of |
| request | | |
| info | | |
| status | | |
| complaint | | |
| other | | |

Overall [ ]/24. Excluding the four ambiguous: [ ]/20.

Confusion pairs, with direction:

| gold | applied | count |
| | | |

The route carrying most of the error is [ ]. The fix is [a definition / a
prompt / a bigger model], because [ ].

### 4. What routing cost

- monolith: [ ] tokens over 24 queries
- router: [ ] tokens over 24 queries
- the classifying call alone: [ ] tokens, which is [ ] per cent of the
  routed total

I predicted that share would be [ ] before measuring it.

[If the share surprised you, say why. The classifier's prompt carries every
route definition on every call, and the specialists carry only their own.]

### 5. What routing bought

One thing a specialist can be forbidden to do that the monolith cannot be
given:

[...]

Would I ship the router: [ ]. Evidence: [ ]. What would change my mind: [ ].

### 6. Stretch variant

Variant assigned: [ ]. Result: [ ].

[For model routing: report both models on accuracy, evidence verbatim, the
confidence range, and resident memory. If the smaller model won, say so
plainly and say what you think that means.]

[For voting: report the split-vote count at each temperature. If nothing
ever disagreed, that is the result. Say what it cost and what it bought.]

### The gold set

`artifacts/goldset.json` now holds [ ] cases: 10 from week 2 and 24 added
today, with the four ambiguous ones tagged.

### Deferred

[Anything you did not get to, and why.]
