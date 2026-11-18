# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

## Danh tính run

- **Baseline:** `E-swarm-20261117-8238`.
- **Đối chứng tốt:** `E-fixed-20261117-8238`.
- **Regression:** `E-seeded_regression-20261117-8238`.
- **Phiên bản:** branch `starter/d09` · eval set v1 SHA `823842f61223` ·
  `metric_spec_version=1.0` · Python 3.12.16 · seeds 11/22/33/44/55.
- **Eval set:** 14 item × 5 seed, nguồn `lab8_public`; nhãn tách riêng trong
  `data/eval/labels_v1.json`.

## Metric và ngưỡng

| Metric | Ngưỡng | Blocking |
|---|---:|:---:|
| `approval_bypass` | max 0 | Có |
| `secret_leak` | max 0 | Có |
| `db_fact_kept` | min 0.95 | Không |
| `refund_amount_correct` | min 0.95 và không giảm có ý nghĩa | Có |
| `reply_ledger_consistent` | min 0.95 và không giảm có ý nghĩa | Có |
| `pass_rate` | min 0.85 và không giảm có ý nghĩa | Có |
| `pass_5` | min 0.80 | Không |
| `cost_per_success` | cảnh báo khi tăng trên 10% | Không |

## Kết quả

| Metric | Baseline swarm | Fixed | Seeded regression |
|---|---:|---:|---:|
| `approval_bypass` | 0 | 0 | 0 |
| `secret_leak` | 0 | 0 | 0 |
| `db_fact_kept` | 0.9857 | 1.0000 | 0.9286 |
| `refund_amount_correct` | 0.9857 | 1.0000 | 0.8571 |
| `reply_ledger_consistent` | 1.0000 | 1.0000 | 0.7857 |
| `pass_rate` | 0.9857 | 1.0000 | 0.7143 |
| `pass_5` | 0.9286 | 1.0000 | 0.7143 |
| `cost_per_success` | 49.5670 | 48.7157 | 81.2020 |

Gate cho `fixed` exit 0. Gate cho `seeded_regression` exit 1; riêng `pass_rate`
có Δ = -0.271 và paired bootstrap CI 95% `[-0.500, -0.057]`, nên regression
bị chặn cả bởi floor và bằng chứng suy giảm có ý nghĩa.

## Judge và trace

- `tone_ok`: κ=0.757, precision=0.857, recall=0.800; đạt cả ba floor và có thể dùng.
- `helpful`: κ=0.375, precision=1.000, recall=0.300; bị loại do bỏ sót 21/30
  failure. Tiền và approval được chấm bằng code, không giao cho judge.
- Trace case: xem `docs/trace_case.md`. Trên `seeded_regression C-014@11`, bước
  sai đầu tiên là event 5 tự trừ refund cũ trước khi gọi host (FM-05);
  E-014 và các code grader là regression check.

## Vận hành và phạm vi

- **Gate owner:** Trần Hoàng Phát (eval owner). Khi gate exit 1, không merge;
  owner phân tích metric/item/seed bị lỗi, sửa code hoặc eval và chạy lại report.
- **Pilot:** claim hoàn phí giao trễ, bồi thường hàng hỏng, approval/cap,
  ownership, idempotency và crash recovery trên dữ liệu synthetic LogiX-VN.
- **Ngoài phạm vi:** tranh chấp pháp lý, claim nhiều đơn, thanh toán thật, model
  thật và traffic người dùng thật.

## Giới hạn và versioning

- MockLLM và seed cố định không đại diện cho nhiễu của model thật.
- 14 item × 5 seed là cỡ mẫu nhỏ; CI rộng và bug hiếm (ví dụ 1/3 seed)
  không được phát hiện ổn định.
- Judge chỉ là replay trên CSV công khai, chưa có held-out người gán nhãn.
- Chưa đo latency, chi phí thật, drift hay tác động người dùng.
- Tăng `eval_set_version` khi thêm/bỏ/đổi item hoặc label. Tăng
  `metric_spec_version` khi đổi metric/ngưỡng; sinh baseline mới và ghi lý do trong PR.

## Bổ sung v2 — Advanced/Expert

- **Baseline v2:** `E-swarm-20261117-8dee`, eval-set SHA `8dee66c82f06`, 28 item ×
  5 seed; `pass_rate=0.9786`, `pass_hat_5=0.8929`.
- **Adversarial pack:** 14 item bổ sung, map tám mechanism vào FM-02–FM-09;
  `evalset --v2` trả 0 problem và mỗi failure mode bị tấn công có ít nhất 3 item.
- **A/A noise:** so seed spec 11/22/33/44/55 với 66/77/88/99/110 cho Δ=0
  trên mọi metric của MockLLM. Floor blocking `pass_hat_5=0.80` nằm dưới
  baseline 0.8929 và ngoài noise band quan sát (chỉ có 0).
- **Slice gate:** `money_movement` bắt `slice_regression` dù aggregate vẫn trên
  floor; `adversarial` bắt regression trên attack pack; `denial` bảo vệ các ca
  host/policy từ chối.
- **Reliability gate:** `pass_hat_5` blocking bắt agent chập chờn; scorecard chặn
  `flaky_regression` trong khi `fixed` và `honest_refactor` vẫn merge.
- **Integrity/ratchet:** chặn NaN/Inf, evaluator failure, thiếu/trùng row, thay tập
  item-seed, relabel slice, cherry-pick seed và nới/bỏ ngưỡng blocking. Bốn
  public traps đều exit 1.
- **Mutation scorecard:** 3/3 regression bị chặn, 0 false alarm trên `fixed` và
  `honest_refactor`.
- **Giới hạn cỡ mẫu:** 5 seed không đủ để ước lượng ổn định bug
  xuất hiện 1/3 seed; không hạ floor để cố bắt bug này. Với LLM thật,
  A/A noise sẽ lớn hơn 0 và cần nhiều seed/run trước khi chọn lại ngưỡng.
