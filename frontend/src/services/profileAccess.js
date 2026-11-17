// Keep capabilities in memory only: closing/reloading the page discards access.
export function createProfileAccess(api) {
  let credential = null;
  const headers = (id) => {
    if (!credential || credential.profile_id !== id) {
      throw new Error('이 프로필의 접근 토큰이 없습니다. 새 프로필을 만들어 주세요.');
    }
    return { headers: { Authorization: `Bearer ${credential.access_token}` } };
  };
  return {
    remember(result) {
      credential = result.profile_id && result.access_token
        ? { profile_id: result.profile_id, access_token: result.access_token } : null;
    },
    clear() { credential = null; },
    async create(profile) {
      const response = await api.post('/api/profile', profile);
      this.remember(response.data);
      return response.data;
    },
    async read(id) { return (await api.get(`/api/profile/${encodeURIComponent(id)}`, headers(id))).data; },
    async update(id, profile) { return (await api.put(`/api/profile/${encodeURIComponent(id)}`, profile, headers(id))).data; },
    async history(id) { return (await api.get(`/api/user/${encodeURIComponent(id)}/history`, headers(id))).data; },
  };
}
