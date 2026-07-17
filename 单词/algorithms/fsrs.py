"""
FSRS (Free Spaced Repetition Scheduler) 算法实现

基于 FSRS-5 算法，为每个词条计算复习间隔和排序优先级。
评级标准 (Rating):
  1 - Again (生疏/忘记)
  2 - Hard (模糊)
  3 - Good (掌握)
  4 - Easy (轻松)
"""

import math
from datetime import datetime, timedelta
from typing import Tuple, Optional


# FSRS-5 默认参数 (经过优化的默认值)
DEFAULT_PARAMS = [
  0.4373, 1.2828, 2.3502, 0.7839,  # w0-w3: 初始稳定性相关
  1.3097, 0.1745, 0.1471, 1.0179,  # w4-w7: 稳定性衰减相关
  1.4060, 0.4811, 1.6927, 0.2594,  # w8-w11: 难度更新相关
  0.8022, 1.0119, 0.9631, 0.2866,  # w12-w15: 稳定性增益相关
  0.6642, 0.1805, 2.0018, 0.8011,   # w16-w18: 额外参数
]


class FSRS:
  """FSRS-5 调度器，管理单张卡片的记忆参数。"""

  def __init__(self, params: Optional[list] = None):
    """
    初始化 FSRS 调度器。
    Args:
      params: 可选的 19 维参数向量，默认为 DEFAULT_PARAMS
    """
    self.w = params if params is not None else DEFAULT_PARAMS.copy()

  @staticmethod
  def _clamp(value: float, low: float, high: float) -> float:
    """将值限制在 [low, high] 区间内。"""
    return max(low, min(high, value))

  def initial_stability(self, rating: int, delta_days: float = 0.0) -> float:
    """
    计算首次复习后的初始稳定性（天数）。
    Args:
      rating: 用户评级 (1-4)
      delta_days: 距离首次学习的天数
    Returns:
      初始稳定性值（天数）
    """
    if rating < 1 or rating > 4:
      rating = 3
    return self.w[0] + self.w[1] * (delta_days + 1) ** self.w[2] * math.exp(self.w[3] * (rating - 1))

  def initial_difficulty(self, rating: int) -> float:
    """
    计算初始难度值。
    Args:
      rating: 用户评级 (1-4)
    Returns:
      难度值 (1-10 区间)
    """
    if rating < 1 or rating > 4:
      rating = 3
    # 初始难度基于评级计算，约束在 1-10
    d0 = self.w[4] - self.w[5] * (rating - 1)
    return self._clamp(d0, 1.0, 10.0)

  def retrievability(self, stability: float, elapsed_days: float) -> float:
    """
    计算当前可提取性 (Retrievability)。
    R(t) = 2^(-t / S)
    Args:
      stability: 当前稳定性（天数）
      elapsed_days: 距离上次复习的天数
    Returns:
      可提取性概率 [0, 1]
    """
    if stability <= 0:
      return 0.0
    return 2.0 ** (-elapsed_days / stability)

  def next_stability(self, difficulty: float, stability: float,
            retrievability: float, rating: int) -> float:
    """
    根据本次复习结果计算新的稳定性。
    Args:
      difficulty: 当前难度
      stability: 当前稳定性
      retrievability: 复习时的可提取性
      rating: 用户评级 (1-4)
    Returns:
      新的稳定性值（天数）
    """
    # 计算稳定性增益因子
    if rating == 1:  # Again - 忘记
      factor = self.w[6] * math.exp(self.w[7] * difficulty)
      new_s = stability * factor
    else:
      # 根据评级计算的稳定性倍率
      mult = self.w[8] + self.w[9] * (rating - 2) * self.w[10]
      # 难度惩罚
      diff_penalty = self.w[11] * (10.0 - difficulty)
      # 可提取性奖励
      ret_bonus = self.w[12] * (1.0 - retrievability)
      # 稳定性衰减系数
      decay = (stability + 1.0) ** self.w[13]

      s_ratio = mult * math.exp(diff_penalty + ret_bonus) * decay

      if rating == 2:  # Hard
        s_ratio *= self.w[14]

      new_s = stability * s_ratio

    return self._clamp(new_s, 0.01, 36500.0)

  def next_difficulty(self, difficulty: float, rating: int) -> float:
    """
    更新难度值。
    Args:
      difficulty: 当前难度
      rating: 用户评级 (1-4)
    Returns:
      新的难度值
    """
    if rating == 1:  # Again - 忘记，增加难度
      delta_d = self.w[15] - self.w[16] * (4.0 - rating)
      new_d = difficulty + delta_d
    else:
      delta_d = self.w[15] - self.w[16] * (4.0 - rating)
      new_d = difficulty + delta_d * (1.0 / (self.w[17] + 1.0))

    # 将难度约束在 1-10 区间
    return self._clamp(new_d, 1.0, 10.0)

  def next_interval(self, stability: float, elapsed_days: float,
           max_interval: float = 3650.0) -> float:
    """
    计算下次复习间隔（天数）。
    Args:
      stability: 新的稳定性值
      elapsed_days: 当前间隔天数
      max_interval: 最大间隔（默认 10 年）
    Returns:
      下次复习间隔（天数）
    """
    # 间隔至少为 1 天，且不超过最大间隔
    interval = stability * self.w[18]
    interval = self._clamp(interval, 1.0, max_interval)
    # 为旧词（间隔 >= 1 天）增加最小间隔保障
    if elapsed_days >= 1.0:
      interval = max(interval, elapsed_days + 1.0)
    return interval

  def schedule(self, rating: int, stability: float, difficulty: float,
          elapsed_days: float, reps: int) -> dict:
    """
    根据本次评级，计算所有新的记忆参数。
    Args:
      rating: 用户评级 (1-4)
      stability: 当前稳定性
      difficulty: 当前难度
      elapsed_days: 距离上次复习的天数
      reps: 历史复习次数
    Returns:
      dict: 包含新参数和下次复习间隔
    """
    if reps == 0:
      # 首次复习，计算初始参数
      new_stability = self.initial_stability(rating, elapsed_days)
      new_difficulty = self.initial_difficulty(rating)
    else:
      # 后续复习
      ret = self.retrievability(stability, elapsed_days)
      new_stability = self.next_stability(difficulty, stability, ret, rating)
      new_difficulty = self.next_difficulty(difficulty, rating)

    new_interval = self.next_interval(new_stability, elapsed_days)

    return {
      "stability": round(new_stability, 2),
      "difficulty": round(new_difficulty, 2),
      "interval": round(new_interval, 1),
      "retrievability": round(
        self.retrievability(new_stability, elapsed_days), 4
      ),
    }

  def get_due_priority(self, stability: float, difficulty: float,
              elapsed_days: float) -> float:
    """
    计算复习优先级分数，用于排序待复习词条。
    分数越低表示越紧急（越应该优先复习）。
    Args:
      stability: 当前稳定性
      difficulty: 当前难度
      elapsed_days: 距离上次复习的天数
    Returns:
      优先级分数
    """
    ret = self.retrievability(stability, elapsed_days)
    return ret * ret  # 低可提取性的词条获得更低的分数（更优先）


# 便捷函数：处理完整的复习请求
def review_card(stability: float, difficulty: float, elapsed_days: float,
        reps: int, rating: int,
        fsrs: Optional[FSRS] = None) -> dict:
  """
  快捷函数：处理一次完整的卡片复习，返回更新后的参数。
  Args:
    stability: 当前稳定性
    difficulty: 当前难度
    elapsed_days: 距离上次复习的天数
    reps: 历史复习次数
    rating: 用户评级 (1-4)
    fsrs: 可选的 FSRS 实例
  Returns:
    dict: 更新后的记忆参数
  """
  if fsrs is None:
    fsrs = FSRS()
  return fsrs.schedule(rating, stability, difficulty, elapsed_days, reps)
