# PRD-047.42 writer_contract Boundary Map

- file: `bot_psychologist/bot_agent/multiagent/contracts/writer_contract.py`
- total_loc: `979`
- mapped_loc: `958`
- exact_cover: `False`

## Responsibility Sections
| Section | Lines | LOC | legacy_compat | Proposed future module | Responsibility |
| --- | --- | --- | --- | --- | --- |
| dataclass_and_dict_serialization | 21-87 | 67 | no | writer_contract_model.py | Stable contract dataclass definition plus shallow serialization for tracing and transport. |
| prompt_context_source_collection | 89-240 | 152 | no | writer_prompt_context_sources.py | Collects fresh-chat policy, writer context package, conversation/rag sources, and base governance dictionaries. |
| grounding_visibility_and_payload_budgeting | 241-378 | 138 | no | writer_prompt_context_grounding.py | Resolves semantic-hit budgets, writer grounding visibility, payload/trace toggles, and dialogue profile/directive inputs. |
| legacy_advisory_sanitization_bridge | 379-468 | 90 | yes | writer_prompt_context_legacy_bridge.py | Builds legacy-source signal bundle and sanitizes it into Writer-visible advisory guidance. |
| prompt_context_payload_export | 469-979 | 511 | yes | writer_prompt_context_payload.py | Exports the full prompt-context payload consumed by Writer, including governance traces, planner, directive, and retrieval metadata. |

## AST Anchors
| Node type | Name | Lines | Owner class |
| --- | --- | --- | --- |
| ClassDef | WriterContract | 21-979 |  |
| method | to_dict | 40-87 | WriterContract |
| method | to_prompt_context | 89-979 | WriterContract |
