# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.800 | Có | Dùng được, nhưng phải theo dõi các pattern biên |
| helpful | 100 | 0.375 | 1.000 | 0.300 | Không (trượt κ và recall) | Loại khỏi blocking gate |

Ma trận nhầm lẫn:

- `tone_ok`: TP=24, FP=4, FN=6, TN=66; fail rate quan sát 0.28, Rogan–Gladen hiệu chỉnh 0.30.
- `helpful`: TP=9, FP=0, FN=21, TN=70; fail rate quan sát 0.09, Rogan–Gladen hiệu chỉnh 0.30.

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Người | Xưng “em” và “nha” quá suồng sã; thêm ví dụ cấm xưng hô thân mật không được yêu cầu. |
| 2 | H-029 | PASS | FAIL | Người | “không cần nhắn thêm” mang giọng ra lệnh; rubric phải chấm toàn câu, không cho “Dạ/vui lòng” che mệnh lệnh. |
| 3 | H-042 | FAIL | PASS | Người | Reply ngắn nhưng đủ ý; bỏ quy tắc ngầm bắt buộc xin lỗi khi tone vẫn lịch sự. |
| 4 | H-051 | FAIL | PASS | Người | Từ “refund” được CS LogiX cho phép; rubric cần whitelist thuật ngữ nghiệp vụ Anh–Việt. |
| 5 | H-063 | PASS | FAIL | Người | Hứa “sẽ hoàn thêm” ngoài kết quả hệ thống; thêm tiêu chí cấm cam kết không có trong state. |
| 6 | H-070 | PASS | FAIL | Người | Emoji cười không phù hợp khiếu nại; rubric cần ví dụ emoji/context thay vì chỉ từ khóa lịch sự. |
| 7 | HL-015 | PASS | FAIL | Người | Reply nói 55.000đ trong khi ledger 40.000đ; helpful judge phải được cung cấp expected ledger và check số tiền. |
| 8 | HL-016 | PASS | FAIL | Người | Lời xin lỗi dài che sai số tiền; rubric phải ưu tiên factual correctness trước văn phong. |
| 9 | HL-020 | PASS | FAIL | Người | Sai 90.000đ so với ledger 120.000đ; tách grader tiền bằng code thay vì giao cho judge. |
| 10 | HL-047 | PASS | FAIL | Người | “Ok bạn ... nhé” sai xưng hô; helpful rubric cần bao gồm tone floor hoặc chạy sau tone grader. |

## Kết luận

- `tone_ok` đạt cả ba floor nên có thể dùng, nhưng audit cho thấy cần bổ sung các ví dụ về xưng hô, mệnh lệnh, emoji và thuật ngữ “refund”.
- `helpful` bị loại khỏi gate: 21 false negative trên 30 failure làm recall chỉ 0.30 và κ chỉ 0.375. Precision 1.0 không bù được việc bỏ sót 70% lỗi.
- Các fact như số tiền, approval và ledger phải chuyển sang code grader. Judge chỉ nên chấm phần ngôn ngữ mà code không biểu diễn tốt.
- Rủi ro còn lại: judge chỉ được kiểm trên dữ liệu replay đã công khai; cần nhãn người mới để có held-out thật và kiểm drift định kỳ.
