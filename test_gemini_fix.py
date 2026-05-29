"""
_gemini_stock_analysis / _gemini_summarize 수정 사항 검증 테스트
- response.text = None 처리
- 빈 응답 재시도
- JSON 배열 없음 재시도
- JSONDecodeError 재시도
- 정상 응답 파싱
"""
import json
import os
import unittest
from unittest.mock import MagicMock, patch

os.environ.setdefault("GEMINI_API_KEY", "fake-key")

import main


def _mock_response(text):
    r = MagicMock()
    r.text = text
    return r


STOCK_SUMMARIES = [
    {
        "symbol": "AAPL",
        "name": "Apple",
        "quote": {"10. change percent": 1.5, "05. price": 200, "09. change": 3.0, "11. currency": "USD"},
        "news": [{"title": "Apple 호실적", "url": "", "source": "Reuters"}],
    }
]

VALID_ANALYSIS = json.dumps([{"comment": "긍정적 흐름", "news_items": ["Apple이 호실적을 발표했다."]}])
VALID_SUMMARIES = json.dumps(["좋은 뉴스 요약입니다."])


class TestGeminiStockAnalysisFix(unittest.TestCase):

    def _patch_generate(self, side_effect):
        return patch.object(
            main.google_genai.Client.return_value.models,
            "generate_content",
            side_effect=side_effect,
        )

    def _run(self, side_effect):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = side_effect
        with patch.object(main.google_genai, "Client", return_value=mock_client):
            with patch("main.time.sleep"):
                return main._gemini_stock_analysis(STOCK_SUMMARIES)

    def test_none_response_returns_empty(self):
        """response.text = None → AttributeError 없이 empty 반환"""
        result = self._run([_mock_response(None)] * 3)
        self.assertEqual(result, [{"comment": "", "news_items": []}])

    def test_empty_string_response_retries_and_returns_empty(self):
        """response.text = '' → 재시도 후 empty 반환"""
        result = self._run([_mock_response("")] * 3)
        self.assertEqual(result, [{"comment": "", "news_items": []}])

    def test_no_json_array_retries_and_returns_empty(self):
        """JSON 배열 없는 응답 → 재시도 후 empty 반환"""
        result = self._run([_mock_response("분석 결과를 제공할 수 없습니다.")] * 3)
        self.assertEqual(result, [{"comment": "", "news_items": []}])

    def test_json_decode_error_retries_and_returns_empty(self):
        """JSONDecodeError → 재시도 후 empty 반환"""
        result = self._run([_mock_response("[broken json {")] * 3)
        self.assertEqual(result, [{"comment": "", "news_items": []}])

    def test_valid_response_returns_data(self):
        """정상 응답 → comment + news_items 정상 반환"""
        result = self._run([_mock_response(VALID_ANALYSIS)])
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0]["comment"], "긍정적 흐름")
        self.assertEqual(result[0]["news_items"], ["Apple이 호실적을 발표했다."])

    def test_none_then_valid_retries_succeed(self):
        """첫 번째 None → 두 번째 정상 응답 → 성공"""
        result = self._run([_mock_response(None), _mock_response(VALID_ANALYSIS)])
        self.assertEqual(result[0]["comment"], "긍정적 흐름")

    def test_empty_then_valid_retries_succeed(self):
        """첫 번째 빈 응답 → 두 번째 정상 응답 → 성공"""
        result = self._run([_mock_response(""), _mock_response(VALID_ANALYSIS)])
        self.assertEqual(result[0]["comment"], "긍정적 흐름")

    def test_rate_limit_retries_with_longer_sleep(self):
        """429 에러 → sleep 후 재시도 → 성공"""
        exc = Exception("Error 429: quota exceeded")
        result = self._run([exc, exc, _mock_response(VALID_ANALYSIS)])
        self.assertEqual(result[0]["comment"], "긍정적 흐름")

    def test_503_unavailable_retries(self):
        """503 UNAVAILABLE → sleep 후 재시도 → 성공"""
        exc = Exception("503 UNAVAILABLE. {'error': {'code': 503, 'message': 'This model is currently experiencing high demand.', 'status': 'UNAVAILABLE'}}")
        result = self._run([exc, _mock_response(VALID_ANALYSIS)])
        self.assertEqual(result[0]["comment"], "긍정적 흐름")

    def test_503_all_attempts_fail_returns_empty(self):
        """503 3회 모두 실패 → empty 반환"""
        exc = Exception("503 UNAVAILABLE")
        result = self._run([exc, exc, exc])
        self.assertEqual(result, [{"comment": "", "news_items": []}])

    def test_json_wrapped_in_markdown(self):
        """```json ... ``` 래핑된 응답도 정상 파싱"""
        wrapped = f"```json\n{VALID_ANALYSIS}\n```"
        result = self._run([_mock_response(wrapped)])
        self.assertEqual(result[0]["comment"], "긍정적 흐름")


class TestGeminiSummarizeFix(unittest.TestCase):

    def _run(self, side_effect):
        mock_client = MagicMock()
        mock_client.models.generate_content.side_effect = side_effect
        with patch.object(main.google_genai, "Client", return_value=mock_client):
            news_items = [{"title": "테스트 뉴스", "desc": "", "source": "매일경제"}]
            return main._gemini_summarize(news_items)

    def test_none_response_returns_empty(self):
        """response.text = None → [] 반환 (AttributeError 없음)"""
        result = self._run([_mock_response(None)])
        self.assertEqual(result, [])

    def test_valid_response_returns_summaries(self):
        """정상 응답 → 요약 리스트 반환"""
        result = self._run([_mock_response(VALID_SUMMARIES)])
        self.assertEqual(result, ["좋은 뉴스 요약입니다."])


if __name__ == "__main__":
    unittest.main()
