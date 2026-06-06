# Project Timeline

```mermaid
gantt
    title Liquid Rocket Project
    dateFormat  YYYY-MM-DD
    section Design
        Requirements freeze           :req,    2026-06-01, 2026-07-01
        Propulsion PDR                :pdr,    after req,  14d
        Propulsion CDR                :cdr,    after pdr,  14d
        Launch System PDR             :lspdr,  after cdr,  7d
        Launch System CDR             :lscdr,  after lspdr, 14d
    section Build & Test
        Component procurement         :proc,   after cdr,  60d
        Cold-flow test            :cf,    after proc, 14d
        Hot-fire test             :hf,    after cf,   14d
```
