import axios from "axios";

const BASE_URL = "http://127.0.0.1:8001";

export const getAllSkills = async () => {
  const res = await axios.get(`${BASE_URL}/skills`);
  return res.data.skills;
};

export const getRecommendations = async (skills, userId) => {  // ← added userId
  try {
    const res = await axios.post(`${BASE_URL}/recommend`, { skills, user_id: userId });
    return res.data;
  } catch (err) {
    console.error("API error:", err);
    return { recommendations: {}, leaf_nodes: [], error: err.message };
  }
};

// ← three new functions below, everything above is unchanged

export const getCareerLevel = async (userId) => {
  const res = await axios.get(`${BASE_URL}/user/${userId}/career`);
  return res.data;
};

export const exportUserData = async (userId) => {
  const res = await axios.get(`${BASE_URL}/user/${userId}/export`);
  return res.data;
};

export const resetUserData = async (userId) => {
  const res = await axios.post(`${BASE_URL}/user/${userId}/reset`);
  return res.data;
};