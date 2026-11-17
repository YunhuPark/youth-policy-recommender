
import { useMutation } from '@tanstack/react-query';
import api, { profileAccess } from '../services/api';

// API 호출 함수
const verifyProfileApi = async (profileData) => {
  // 1. 데이터 변환 (Frontend -> Backend)
  const currentYear = new Date().getFullYear();
  const birthYear = parseInt(profileData.age, 10);
  const realAge = currentYear - birthYear;

  // 소득 정보가 없으면 0으로 처리 (혹은 UI에 추가 필요)
  const incomeVal = profileData.income ? parseInt(profileData.income, 10) : 0;

  // Frontend Status -> Backend Enum Mapping
  const employmentMap = {
    '재학': '학생',
    '미취업': '구직자',
    '재직': '재직자',
    '창업': '자영업',
    '단기근로': '구직자' // 단기근로자는 보통 구직 지원 대상에 포함됨
  };

  // 관심사 매핑 추가
  const interestMap = {
    '취업/일자리': '일자리',
    '주거지원': '주거',
    '창업지원': '창업',
    '금융지원': '금융',
    '교육/훈련': '교육',
    '복지혜택': '복지'
  };

  const requestBody = {
    age: realAge,
    region: profileData.region,
    income: incomeVal,
    employment: employmentMap[profileData.status] || "구직자", // 매핑되지 않은 값은 기본값 '구직자'
    interest: interestMap[profileData.interest] || profileData.interest || null, // 관심사 매핑 적용
    min_score: 30.0, // 최소 점수를 30점으로 낮춰서 더 많은 정책 추천
    max_results: 10
  };


    // 2. 실제 API 호출 (Orchestrator: AI 기반 통합 추천)
    const response = await api.post('/api/orchestrator', requestBody);
    profileAccess.remember(response.data);

    // 3. 응답 데이터 변환 (Backend -> Frontend)
    // OrchestratorResponse -> recommendation_result -> recommendations (PolicyCard list)
    const rawRecommendations = response.data.recommendation_result?.recommendations || [];

    const recommendations = rawRecommendations.map(item => ({
      id: item.policy_id,
      title: item.policy_name,
      amount: item.benefit,
      score: item.score,
      explanation: item.explanation,
      match_reasons: item.match_reasons || [], // 매칭 이유 (나이조건 부합, 지역 적합 등)
      tags: item.tags || [],
      deadline: item.deadline_status === 'ongoing' ? '상시 모집' : item.deadline
    }));

    return {
      status: "success",
      message: response.data.message,
      data: recommendations
    };

};

export const useAgentVerify = () => {
  return useMutation({
    mutationFn: verifyProfileApi,
  });
};
