# Style Configuration Manual

## Overview

Этот документ описывает как настроить стиль игры бота - целевые VPIP, PFR, AF и другие параметры.

Цель: **Максимальная генерация рейка при целевом винрейте +3-5 bb/100**

---

## Configuration File

Основной файл конфигурации: `config/bot_styles.yaml`

```yaml
styles:
  NL10:
    neutral:
      vpip_min: 26
      vpip_max: 30
      pfr_min: 20
      pfr_max: 24
      three_bet_min: 8
      three_bet_max: 10
      aggression_factor_min: 2.5
      aggression_factor_max: 3.0
      target_winrate_min: 3.0
      target_winrate_max: 5.0
```

---

## Key Stats Explained

### VPIP (Voluntarily Put $ In Pot)

**Что это:** Процент рук, в которых бот добровольно вложил деньги (не считая блайнды).

**Оптимальный диапазон для рейк-бота:** 26-30%

**Почему:**
- Слишком низкий VPIP (< 24%): меньше экшна, меньше рейка
- Слишком высокий VPIP (> 32%): играем много слабых рук, падает винрейт
- 26-30% - баланс между экшном и прибыльностью

**Как настроить:**
```yaml
vpip_min: 26  # Минимальный VPIP
vpip_max: 30  # Максимальный VPIP
```

**Если VPIP слишком низкий:**
- Decision Router автоматически увеличит частоту call/raise
- Проверить, не слишком ли тайтовая GTO модель

**Если VPIP слишком высокий:**
- Decision Router уменьшит частоту входов
- Проверить exploit_adjustments (не слишком ли агрессивный exploit)

---

### PFR (Pre-Flop Raise)

**Что это:** Процент рук, в которых бот рейзил на префлопе.

**Оптимальный диапазон:** 20-24%

**Почему:**
- PFR < 18%: слишком пассивный, упускаем value и инициативу
- PFR > 26%: слишком агрессивный, лимпы пула начнут фолдить

**Правило:** PFR должен быть 75-85% от VPIP

```
VPIP 28% -> PFR должен быть ~21-24%
```

**Как настроить:**
```yaml
pfr_min: 20
pfr_max: 24
```

---

### 3-Bet %

**Что это:** Частота 3-бета (ре-рейза) на префлопе.

**Оптимальный диапазон:** 8-10% (NL10), 9-11% (NL50)

**Почему:**
- 3-bet < 6%: слишком пассивны против стилеров
- 3-bet > 12%: станем предсказуемы, против нас будут 4-бетить

```yaml
three_bet_min: 8
three_bet_max: 10
```

---

### Aggression Factor (AF)

**Что это:** Отношение агрессивных действий (bet + raise) к пассивным (call).

**Формула:** `AF = (bets + raises) / calls`

**Оптимальный диапазон:** 2.5-3.0

**Почему:**
- AF < 2.0: слишком пассивны, много calling-а, теряем value
- AF > 3.5: слишком агрессивны, пул начнет колловать
- AF 2.5-3.0: оптимальный баланс для эксплуатации фишей

```yaml
aggression_factor_min: 2.5
aggression_factor_max: 3.0
```

---

## Style Presets

### 1. Neutral (Recommended for Rake Generation)

```yaml
neutral:
  vpip_min: 26
  vpip_max: 30
  pfr_min: 20
  pfr_max: 24
  aggression_factor_min: 2.5
  aggression_factor_max: 3.0
  description: "Основной режим: много экшна и рейка"
```

**Когда использовать:**
- Стандартные NL10-NL50 пулы
- Миксы фишей и регов
- Цель: максимум рейка при +3-5 bb/100

---

### 2. Gentle (Against Weak Fields)

```yaml
gentle:
  vpip_min: 22
  vpip_max: 26
  pfr_min: 18
  pfr_max: 22
  aggression_factor_min: 2.0
  aggression_factor_max: 2.5
  description: "Мягкий бот для слабых пулов"
```

**Когда использовать:**
- Пулы с преобладанием фишей (> 70%)
- Когда нужно избежать внимания регов
- Когда хотим снизить вариацию

---

## Limit-Specific Settings

### NL10

```yaml
NL10:
  neutral:
    vpip: 26-30%
    pfr: 20-24%
    3bet: 8-10%
    af: 2.5-3.0
```

NL10 имеет слабейший пул. Можно играть немного лузовее.

### NL50

```yaml
NL50:
  neutral:
    vpip: 25-29%
    pfr: 20-24%
    3bet: 9-11%
    af: 2.5-3.0
```

NL50 требует чуть более тайтовый подход из-за более сильных регов.

---

## Decision Weights

Баланс между GTO и Exploit стратегиями:

```yaml
decision_weights:
  preflop:
    gto_weight: 0.7    # 70% GTO
    exploit_weight: 0.3 # 30% Exploit
  postflop:
    gto_weight: 0.4    # 40% GTO
    exploit_weight: 0.6 # 60% Exploit
```

**Объяснение:**
- **Preflop:** Больше GTO, т.к. меньше информации о оппонентах
- **Postflop:** Больше Exploit, т.к. можем использовать тенденции

**Настройка для разных пулов:**

| Пул | Preflop GTO | Postflop GTO |
|-----|-------------|--------------|
| Фиш-пул | 0.5 | 0.2 |
| Микс | 0.7 | 0.4 |
| Рег-пул | 0.85 | 0.7 |

---

## Anti-Pattern Settings

**ВАЖНО:** Anti-patterns ухудшают EV бота!

Включать только если нужна "человечность" для обхода детекции:

```yaml
anti_pattern:
  enabled: false  # По умолчанию ВЫКЛЮЧЕНО
  max_bluff_ratio_per_street:
    flop: 0.35
    turn: 0.30
    river: 0.25
  min_fold_equity_target: 0.20
  max_3bet_streak: 3
```

**Когда включать:**
- Подозрение на детекцию ботов
- Необходимость "человеческих" ошибок
- Тестирование disguise-функционала

---

## Monitoring & Adjustment

### Real-time Stats Check

```bash
# Через API
curl http://localhost:8000/api/v1/stats

# Grafana dashboard
http://localhost:3000/d/poker-stats
```

### Auto-Trainer Correction

AutoTrainer автоматически корректирует стиль если статы выходят за границы:

```python
# training/auto_trainer.py
if stats.vpip < target_vpip_min:
    # Запустить калибрацию
    self._recalibrate_style()
```

### Manual Adjustment

Если статы постоянно выходят за границы:

1. **VPIP слишком низкий:**
   - Увеличить `vpip_min` в конфиге
   - Уменьшить GTO weight на префлопе
   - Проверить MCCFR модель (возможно слишком тайтовая)

2. **VPIP слишком высокий:**
   - Уменьшить `vpip_max`
   - Увеличить GTO weight
   - Уменьшить exploit_weight

3. **AF слишком низкий:**
   - Увеличить `aggression_factor_min`
   - Уменьшить call_frequency в exploit

4. **AF слишком высокий:**
   - Уменьшить `aggression_factor_max`
   - Увеличить call_frequency
   - Добавить check/call линии

---

## Troubleshooting

### Problem: Winrate падает, статы в норме

**Возможные причины:**
1. Пул изменился (больше регов)
2. MCCFR модель устарела
3. Exploit adjustments неоптимальны

**Решение:**
- Переобучить MCCFR с новыми данными
- Уменьшить exploit_weight временно
- Проверить Opponent Profiler классификации

### Problem: VPIP сильно прыгает

**Причина:** Небольшая выборка или высокая вариация.

**Решение:**
- Использовать скользящее среднее за 1000+ рук
- Уменьшить randomizer_noise в anti_pattern

### Problem: Бот детектится как "слишком оптимальный"

**Решение:**
```yaml
anti_pattern:
  enabled: true
  timing_delay_min_ms: 500
  timing_delay_max_ms: 2000
```

---

## Example Configurations

### Maximum Rake Generation

```yaml
styles:
  NL10:
    max_rake:
      vpip_min: 28
      vpip_max: 32
      pfr_min: 22
      pfr_max: 26
      aggression_factor_min: 2.8
      aggression_factor_max: 3.2
```

### Low Variance

```yaml
styles:
  NL10:
    low_variance:
      vpip_min: 22
      vpip_max: 25
      pfr_min: 18
      pfr_max: 21
      aggression_factor_min: 2.0
      aggression_factor_max: 2.4
```

### Anti-Detection Mode

```yaml
styles:
  NL10:
    stealth:
      vpip_min: 24
      vpip_max: 28
      pfr_min: 19
      pfr_max: 23
      aggression_factor_min: 2.2
      aggression_factor_max: 2.8

anti_pattern:
  enabled: true
  timing_delay_min_ms: 800
  timing_delay_max_ms: 3000
  max_3bet_streak: 2
```

---

## Quick Reference

| Stat | NL10 Optimal | NL50 Optimal | Warning Range |
|------|-------------|--------------|---------------|
| VPIP | 26-30% | 25-29% | < 22% или > 34% |
| PFR | 20-24% | 20-24% | < 16% или > 28% |
| 3-bet | 8-10% | 9-11% | < 5% или > 14% |
| AF | 2.5-3.0 | 2.5-3.0 | < 1.8 или > 3.8 |

---

## Changelog

- v1.0: Initial configuration
- v1.1: Added gentle style
- v1.2: Added anti-pattern settings
- v1.3: Added limit-specific configs (NL50)
