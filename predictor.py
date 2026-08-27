import random
import time
import psutil
import requests
#from price_oracle import get_aws_price, get_azure_price, get_gcp_price

#CONFIGURATION

POP_SIZE = 30
GENERATIONS = 60
MUTATION = 0.12
CLOUDS = ["AWS", "GCP", "Azure"]
SAMPLES = 10

SLA_SCORE = {"AWS": 0.9999, "GCP":0.9995, "Azure": 0.9997}
LATENCY = {"AWS": 12, "GCP": 18, "Azure": 15}
MIGRATION_COST_PER_SEC = 0.002
MIGRATION_TIME_SEC = 30

#REAL SYSTEM METRICS USING PSUTIL

def get_system_metrics():
    cpu = psutil.cpu_percent(interval=1)
    ram = psutil.virtual_memory().percent
    net = psutil.net_io_counters()
    mbps = round((net.bytes_sent + net.bytes_recv) / 1024 / 1024, 1)
    return {
       "cpu_percent": cpu,
       "ram_percent": ram,
       "network_mbps": mbps,
    }

#PRICE TREND ANALYSIS

def calculate_trend(prices):
   if len(prices) < 2:
      return 0
   diffs = [prices[i+1] - prices[i] for i in range(len(prices)-1)]
   return sum(diffs) / len(diffs)

def get_trend_penalty(history, cloud):
   trend = calculate_trend(history[cloud])
   if trend > 0.01:
      return 0.05
   elif trend < -0.01:
      return -0.03
   return 0

#MIGRATION FREQUENCY PENALTY

def migration_penalty(individual):
   switches = sum(1 for i in range(1, len(individual))
        if individual[i] != individual[i-1])
   return switches * MIGRATION_COST_PER_SEC * MIGRATION_TIME_SEC

#FITNESS FUNCTION - ALL REAL FUNCTIONS

def fitness(individual, history, metrics):
   score = 0
   for i, cloud_idx in enumerate(individual):
       cloud = CLOUDS[cloud_idx]
       score -= history[cloud][i] * 10
       cpu_risk = metrics["cpu_percent"] / 100
       ram_risk = metrics["ram_percent"] / 100
       score -= (cpu_risk + ram_risk) * 0.5
       score -= get_trend_penalty(history, cloud) * 5
       score -= LATENCY[cloud] * 0.001
       score += SLA_SCORE[cloud] * 2
   score -= migration_penalty(individual) * 10
   return score

#GENETIC ALGORITHM

def run_ga(history, metrics):
  steps = len(history["AWS"])
  population = [
     [random.randint(0, 2) for _ in range(steps)]
     for _ in range(POP_SIZE)
  ]
  print(f"\n Running Genetic Algorithm...")
  print(f" Population:{POP_SIZE} | Generations:{GENERATIONS} | Mutation:{MUTATION}")
  for gen in range(GENERATIONS):
     scored = sorted(population, 
                     key=lambda x:fitness(x, history, metrics),
                     reverse=True)
     survivors = scored[:POP_SIZE // 2]
     children = []
     for _ in range(POP_SIZE // 2):
        p1, p2 = random.sample(survivors, 2)
        cut = random.randint(1, steps - 1)
        child = p1[:cut] + p2[cut:]
        children.append(child)
     for child in children:
        for j in range(steps):
           if random.random() < MUTATION:
              child[j] = random.randint(0, 2)

     population = survivors + children

     if gen % 15 == 0:
        best_f = fitness(scored[0], history, metrics)
        print(f"Gen {gen:3d} -> Fitness: {best_f:.4f}")
  return max(population, key=lambda x: fitness(x, history, metrics))

#COLLECT REAL PRICE HISTORY

def collect_prices():
    """
    Demo mode: use local fallback price history.
    AWS shows a rising price trend so the predictor
    can demonstrate an approaching price spike.
    """

    history = {
        "AWS":   [0.20, 0.22, 0.24, 0.27, 0.30, 0.33, 0.36, 0.40, 0.44, 0.48],
        "GCP":   [0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.16, 0.16],
        "Azure":  [0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18, 0.18]
    }

    print("Using fallback/demo price data...")
    
    for i in range(SAMPLES):
        print(
            f" [{i+1}/{SAMPLES}] "
            f"AWS:${history['AWS'][i]:.4f} "
            f"GCP:${history['GCP'][i]:.4f} "
            f"Azure:${history['Azure'][i]:.4f}"
        )

    return history

#MAIN

if __name__ == "__main__":
   print("=" * 55)
   print("AI PREDICTOR v2.0 - Real Data + Genetic algorithm")
   print("=" * 55)
   history = collect_prices()
   print("\n Reading real system metrics...")
   metrics = get_system_metrics()
   print(f" CPU usage : {metrics['cpu_percent']}%")
   print(f" RAM usage : {metrics['ram_percent']}%")
   print(f" Network : {metrics['network_mbps']} MB transferred")
   print(f" Price Trends (last {SAMPLES}  samples):")
   for cloud in CLOUDS:
      trend = calculate_trend(history[cloud])
      if trend > 0.01:
         direction = "RISING"
      elif trend < -0.01:
         direction = "FALLING"
      else:
         direction = "STABLE"
      print(f" {cloud:5s}: {direction} ({trend:+.4f}/sample)")
   best_plan = run_ga(history, metrics)
   counts = {c: best_plan.count(i) for i, c in enumerate(CLOUDS)}
   predicted = max(counts, key=counts.get)
   migrations = sum(1 for i in range(1, len(best_plan))
             if best_plan[i] != best_plan[i-1])
   avg_prices = {c: round(sum(history[c])/len(history[c]), 4) for c in CLOUDS}
   
   print("\n" + "=" * 55)
   print("RESULTS")
   print("=" * 55)
   print(f"\n Average prices: ")
   for c in CLOUDS:
      print(f" {c:5s} -> ${avg_prices[c]}/hr | "
            f"Latency:{LATENCY[c]}ms | SLA:{SLA_SCORE[c]*100:.2f}%")
   print(f"\n GA Migration Plan: ")
   for c in CLOUDS:
      bar = "=" * counts[c]
      print(f" {c:5s}: [{bar}] {counts[c]} steps")
   print(f"\n Total migrations : {migrations}")
   print(f" Migration cost : ${migrations * MIGRATION_COST_PER_SEC * MIGRATION_TIME_SEC:.4f}")
   print(f"\n MIGRATE TO ---> {predicted}")
        # AUTOMATIC MIGRATION TRIGGER
   if predicted == "GCP":
     print("\n🚨 PRICE SPIKE PREDICTED!")
     print("🤖 AI decision: Migrate workload AWS → GCP")
     print("🚀 Triggering migration automatically...")

     try:
        response = requests.post(
            "http://192.168.88.10:8888/migrate",
            json={
                "service": "counter-app",
                "target_vm": "GCP",
                "target_ip": "192.168.88.14"
            },
            timeout=10
        )

        print(f"Migration controller response: {response.text}")

     except Exception as e:
        print(f"Migration trigger failed: {e}")
   print(f" factors used: Price +Trend + Real CPU/RAM + Latency + SLA + Cost")
   print("=" * 55)

