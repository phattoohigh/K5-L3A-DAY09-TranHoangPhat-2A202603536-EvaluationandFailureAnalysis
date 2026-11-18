# Research card

File này nằm cố định ở `report/team/research_card.md`; `python -m lab8.check_submission` đọc cột "Nhóm điền" bằng máy.

Phần này nối tiếp phần mini research ở buổi lý thuyết (slide 62–63). Chọn **một** câu R1–R4, điền 6 dòng, rồi biến nó thành **một ablation** chạy được trong lab: giữ nguyên model (MockLLM), tool, seed, corpus và giá, chỉ thay đổi một biến.

| Câu | Nguồn (thư viện tham khảo, slide 68–69) | Câu hỏi gợi ý cho lab |
| --- | --- | --- |
| R1 · Scaling | Google Research 2026, *Towards a Science of Scaling Agent Systems* | Task claims chủ yếu tuần tự hay song song được? Dự đoán thêm investigator sẽ làm pass rate và cost/success thay đổi thế nào. |
| R2 · Failure taxonomy | MAST, NeurIPS 2025, *Why Do Multi-Agent LLM Systems Fail?* | Các trial fail của swarm (seed 55) thuộc nhóm nào: lỗi giao việc, lệch mục tiêu, hay lỗi kiểm chứng? |
| R3 · Architecture choices | AgentArch, AACL 2026 | Nếu đổi topology mà giữ nguyên mọi thứ khác, biến nào phải cố định để kết luận còn đúng? |
| R4 · Evaluation confounders | EMNLP 2026, *Rethinking Evaluation of MAS Efficiency* | Làm sao chứng minh chênh lệch giữa A/B/C/D là do topology, không phải do prompt, tool hay seed? |

## Phiếu của nhóm

Điền vào cột cuối. Không xóa hai cột đầu.

| Field | Hướng dẫn | Nhóm điền |
| --- | --- | --- |
| CÂU | R1 / R2 / R3 / R4 | R1 · Scaling |
| SOURCE | Paper/blog, năm, URL, loại bằng chứng (benchmark, production report, blog kinh nghiệm) | Google Research, Google DeepMind và MIT, *Towards a Science of Scaling Agent Systems*, arXiv:2512.08296 (v1 tháng 12/2025), https://arxiv.org/abs/2512.08296; bài blog Google Research 28/01/2026. Loại bằng chứng: benchmark có kiểm soát (nhiều cấu hình × 6 benchmark agentic × 5 kiến trúc × 3 họ LLM) |
| CLAIM | Một kết luận gốc của nguồn. Không viết rộng hơn phạm vi paper | Thêm agent không phải lúc nào cũng tốt hơn. Lợi ích của phối hợp giảm dần khi baseline single-agent đã cao, và task nặng về tool chịu thêm chi phí phối hợp của multi-agent |
| BOUNDARY | Model / dataset / setup giới hạn kết luận đó | Đo trên LLM thật của 3 họ model và 6 benchmark agentic của paper, không có task hoàn tiền nào. Lab dùng MockLLM cố định theo seed, 14 claim public, dữ kiện đã có cấu trúc trong SQLite. Kết luận chỉ chuyển sang lab ở mức hướng đi, không ở mức con số |
| HYPOTHESIS | Nếu đổi shape A→B (hoặc bật/tắt một thành phần), metric X sẽ đổi theo hướng nào, khoảng bao nhiêu | Claim là task tuần tự ngắn, nặng tool, và baseline workflow đã pass 1.0. Vì vậy bật lớp investigator (workflow A → orchestrator C) sẽ **không** tăng pass rate (giữ 1.0), nhưng cost/success tăng khoảng 1.5–2.5 lần và số tool call mỗi trial tăng theo |
| METHOD | Biến giữ cố định: model, tools, seed, corpus, giá, evaluator. Biến duy nhất được thay đổi: … | Giữ cố định: MockLLM, `tools.manifest.v1.1.yaml`, seed 11,22,33,44,55, `data/public_claims.jsonl`, `config/pricing.yaml`, evaluator `metrics.trial_pass`, cửa ghi `durability.issue_refund` với quote đầy đủ, mỗi trial một SQLite mới. Biến duy nhất được thay đổi: có hay không lớp handoff + investigator chỉ đọc trước khi orchestrator quote (A không có, C có) |
| FAILURE / METRIC | Một lỗi dự kiến và cách đo nó: pass rate, pass^5, variance, cost/success, leak, bypass | Lỗi dự kiến: chi phí phối hợp (thêm model call `plan`, thêm `lookup_policy`, `lookup_refund_history` mà không đổi quyết định), cộng thêm rủi ro rò secret qua handoff. Đo bằng cost/success, mean_tool_calls, pass rate, pass^5, variance; leak đo bằng `test_no_secret_or_pii_in_any_public_trace` |

## Kết quả ablation

- Lệnh đã chạy (copy nguyên văn): `python -m lab8.benchmark --shapes workflow,orchestrator --cases data/public_claims.jsonl --seeds 11,22,33,44,55 --out reports/ablation_r1.json`
- Run id / file report: `src/reports/ablation_r1.json` (70 trial mỗi shape, ví dụ R-workflow-C-014-s33 và R-orchestrator-C-014-s33); số khớp `src/reports/benchmark.json`
- Kết quả so với hypothesis (đúng / sai / không kết luận được), kèm số liệu: **Đúng.** Pass rate giữ nguyên (workflow 1.000, orchestrator 1.000; pass^5 1.000 cả hai; variance 0 cả hai). Cost/success tăng 28.79 → 57.19 VND (×1.99), mean tool call mỗi trial 2.79 → 5.57 (×2.0), mean model call 1 → 2. Không trial nào rò secret hay PII ở cả hai shape. Lớp investigator chỉ thêm chi phí, không thêm độ đúng trên bộ này
- Giới hạn: MockLLM không phải model sản xuất, latency là `unavailable`. MockLLM không "hiểu sai" theo kiểu LLM thật nên ablation không đo được lợi ích tiềm năng của investigator khi ticket mơ hồ. Chỉ 14 claim public; kết quả trên hidden có thể khác. Orchestrator cũng gọi thêm tool mà workflow không gọi, nên "lớp investigator" ở đây gồm cả các tool đó, không tách riêng được.

Muốn đi xa hơn một ablation để lấy điểm cộng thì xem [docs/bonus_topics.md](../../docs/bonus_topics.md).
