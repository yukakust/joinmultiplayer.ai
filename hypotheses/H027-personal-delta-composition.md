# H027 — Personal delta composition

question: Can independently personalized towers return bounded, compatible neural deltas that a source model composes into an answer unavailable to its base path or either tower alone?

why it might be true: A shared initialization and frozen neural ABI give every personal tower a common latent grammar, while local weight updates encode what that pocket i adds beyond the base.

smallest useful test: Teach eight towers four disjoint synthetic specialties, require two specialties per answer, compare `FinalLayers(z0 + Merge(delta1, delta2))` against the frozen base, fresh clones, and separately trained single-role controls, then force every preferred expert to fail and require the second distinct expert to preserve the result.
