"""
QUANTUM DECISION SIMULATOR V4
Fully optimized for RTX 3050 + i5-12400F (12 threads)

Uses BOTH GPU and CPU in perfect harmony for maximum performance

Installation:
1. Check CUDA version: nvidia-smi
2. Uninstall conflicts: pip uninstall cupy-cuda11x cupy-cuda12x cupy-cuda13x cupy
3. Install matching CuPy:
   - CUDA 11.x: pip install cupy-cuda11x
   - CUDA 12.x: pip install cupy-cuda12x
   - CUDA 13.x: pip install cupy-cuda12x  (Drivers are backward compatible)
4. pip install numpy scipy psutil gputil matplotlib seaborn

Usage:
    from quantum_simulator import QuantumSimulator
    
    qs = QuantumSimulator()
    result = qs.analyze_decision(
        "Should I invest $5000 in Bitcoin?",
        context={
            'amount': 5000,
            'investment_type': 'bitcoin',
            'risk_tolerance': 'medium'
        }
    )
"""

import numpy as np
import time
import platform
import subprocess
import warnings
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Dict, List, Any, Tuple
import json
from datetime import datetime, timedelta

# Hardware Detection
import psutil
try:
    import GPUtil
    GPUTIL_AVAILABLE = True
except:
    GPUTIL_AVAILABLE = False
    print("⚠️  GPUtil not found: pip install gputil")

# GPU Acceleration
try:
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message=".*CUDA path.*")
        import cupy as cp
    # Test if cupy can actually initialize and use the GPU for random generation
    cp.empty(1)
    cp.random.normal(0, 1, size=(1,))
    CUPY_AVAILABLE = True
    print("✅ CuPy detected - GPU acceleration enabled")
except Exception as e:
    cp = np
    CUPY_AVAILABLE = False
    print(f"⚠️  CuPy failed to initialize ({e})")
    if "attribute 'empty'" in str(e):
        print("   👉 Hint: Bad install. Run: pip uninstall -y cupy cupy-cuda13x && pip install cupy-cuda12x")
    elif "curand" in str(e) or "cudart" in str(e):
        print("   👉 Hint: Missing CUDA DLLs. Run: pip uninstall -y cupy && pip install cupy-cuda12x")
    print("   (GPU acceleration disabled, using CPU only)")

# Visualization
try:
    import matplotlib.pyplot as plt
    import seaborn as sns
    VISUALIZATION_AVAILABLE = True
    sns.set_style("darkgrid")
except:
    VISUALIZATION_AVAILABLE = False
    print("⚠️  Matplotlib/Seaborn not found: pip install matplotlib seaborn")


# ============================================================================
# HARDWARE DETECTOR
# ============================================================================

class HardwareDetector:
    """Auto-detects and optimizes for your specific hardware"""
    
    def __init__(self):
        self.specs = self._detect_hardware()
        self._optimize_settings()
        
    def _detect_hardware(self) -> Dict:
        """Detect all hardware specs"""
        specs = {
            'cpu': {
                'name': platform.processor(),
                'cores': psutil.cpu_count(logical=False),
                'threads': psutil.cpu_count(logical=True),
                'freq_max': psutil.cpu_freq().max if psutil.cpu_freq() else 0
            },
            'ram': {
                'total_gb': round(psutil.virtual_memory().total / (1024**3), 1),
                'available_gb': round(psutil.virtual_memory().available / (1024**3), 1)
            },
            'gpu': self._detect_gpu()
        }
        return specs
    
    def _detect_gpu(self) -> Dict:
        """Detect GPU (NVIDIA preferred)"""
        # Try GPUtil first
        if GPUTIL_AVAILABLE:
            try:
                gpus = GPUtil.getGPUs()
                if gpus:
                    gpu = gpus[0]
                    return {
                        'available': True,
                        'name': gpu.name,
                        'memory_gb': round(gpu.memoryTotal / 1024, 1),
                        'cuda_cores': self._estimate_cuda_cores(gpu.name)
                    }
            except:
                pass
        
        # Fallback: nvidia-smi
        try:
            result = subprocess.run(
                ['nvidia-smi', '--query-gpu=name,memory.total', '--format=csv,noheader'],
                capture_output=True, text=True, timeout=2
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split(',')
                name = parts[0].strip()
                memory = float(parts[1].strip().split()[0]) / 1024
                return {
                    'available': True,
                    'name': name,
                    'memory_gb': memory,
                    'cuda_cores': self._estimate_cuda_cores(name)
                }
        except:
            pass
        
        return {'available': False}
    
    def _estimate_cuda_cores(self, gpu_name: str) -> int:
        """Estimate CUDA cores based on GPU model"""
        gpu_name = gpu_name.upper()
        
        # RTX 3050 variants
        if '3050' in gpu_name:
            return 2560 if 'DESKTOP' in gpu_name or 'TI' in gpu_name else 2048
        
        # Common GPUs
        cuda_map = {
            '4090': 16384, '4080': 9728, '4070': 5888, '4060': 3072,
            '3090': 10496, '3080': 8704, '3070': 5888, '3060': 3584,
            '2080': 2944, '2070': 2304, '2060': 1920,
            '1080': 2560, '1070': 1920, '1660': 1408
        }
        
        for model, cores in cuda_map.items():
            if model in gpu_name:
                return cores
        
        return 2048  # Default
    
    def _optimize_settings(self):
        """Calculate optimal settings"""
        threads = self.specs['cpu']['threads']
        
        # CPU optimization
        if threads >= 12:
            self.cpu_mode = 'aggressive'
            self.max_workers = 12
            self.batch_size = 1000
        elif threads >= 8:
            self.cpu_mode = 'balanced'
            self.max_workers = 8
            self.batch_size = 800
        else:
            self.cpu_mode = 'conservative'
            self.max_workers = 4
            self.batch_size = 500
        
        # GPU optimization
        if self.specs['gpu']['available'] and CUPY_AVAILABLE:
            cuda_cores = self.specs['gpu']['cuda_cores']
            gpu_memory = self.specs['gpu']['memory_gb']
            
            if cuda_cores >= 2000 and gpu_memory >= 4:
                self.gpu_mode = 'enabled'
                self.gpu_batch_size = min(50000, cuda_cores * 20)
                self.use_gpu_threshold = 5000
            else:
                self.gpu_mode = 'light'
                self.gpu_batch_size = 10000
                self.use_gpu_threshold = 10000
        else:
            self.gpu_mode = 'disabled'
            self.gpu_batch_size = 0
            self.use_gpu_threshold = float('inf')
        
        # Memory optimization
        ram_gb = self.specs['ram']['total_gb']
        if ram_gb >= 16:
            self.max_simulations = 100000
        elif ram_gb >= 8:
            self.max_simulations = 50000
        else:
            self.max_simulations = 20000
    
    def should_use_gpu(self, num_simulations: int) -> bool:
        """Decide if GPU should be used"""
        return (self.specs['gpu']['available'] and 
                num_simulations >= self.use_gpu_threshold and
                self.gpu_mode != 'disabled')
    
    def print_info(self):
        """Print hardware information"""
        s = self.specs
        print("\n" + "="*60)
        print("🖥️  HARDWARE DETECTION")
        print("="*60)
        print(f"\n💻 CPU:")
        print(f"   • Processor: {s['cpu']['name'][:50]}")
        print(f"   • Cores: {s['cpu']['cores']} physical, {s['cpu']['threads']} threads")
        print(f"   • Optimization: {self.cpu_mode.upper()} ({self.max_workers} workers)")
        
        print(f"\n🧠 RAM:")
        print(f"   • Total: {s['ram']['total_gb']} GB")
        print(f"   • Available: {s['ram']['available_gb']} GB")
        
        print(f"\n🎮 GPU:")
        if s['gpu']['available']:
            print(f"   • Model: {s['gpu']['name']}")
            print(f"   • VRAM: {s['gpu']['memory_gb']} GB")
            print(f"   • CUDA Cores: ~{s['gpu']['cuda_cores']:,}")
            print(f"   • Mode: {self.gpu_mode.upper()}")
            print(f"   • Threshold: {self.use_gpu_threshold:,} simulations")
        else:
            print("   • Status: No CUDA GPU detected")
            print("   • Mode: CPU-only")
        
        print("\n" + "="*60 + "\n")


# ============================================================================
# GPU ACCELERATOR
# ============================================================================

class GPUAccelerator:
    """GPU-accelerated operations using CuPy"""
    
    def __init__(self, hardware: HardwareDetector):
        self.hardware = hardware
        self.gpu_available = CUPY_AVAILABLE and hardware.specs['gpu']['available']
        
        if self.gpu_available:
            # Set memory limit (leave some for system)
            mempool = cp.get_default_memory_pool()
            max_memory = int(hardware.specs['gpu']['memory_gb'] * 0.8 * 1024**3)
            mempool.set_limit(size=max_memory)
    
    def to_gpu(self, array):
        """Move array to GPU"""
        return cp.asarray(array) if self.gpu_available else array
    
    def to_cpu(self, array):
        """Move array to CPU"""
        if self.gpu_available and isinstance(array, cp.ndarray):
            return cp.asnumpy(array)
        return array
    
    def generate_random_normal(self, shape, mean=0, std=1):
        """Generate random normal distribution on GPU"""
        if self.gpu_available:
            return cp.random.normal(mean, std, size=shape)
        return np.random.normal(mean, std, size=shape)
    
    def cumulative_product(self, array, axis=1, initial_value=1.0):
        """Calculate cumulative product on GPU"""
        if self.gpu_available:
            return cp.cumprod(array, axis=axis) * initial_value
        return np.cumprod(array, axis=axis) * initial_value
    
    def calculate_statistics(self, data):
        """Calculate statistics on GPU"""
        if self.gpu_available:
            data_gpu = self.to_gpu(data)
            stats = {
                'mean': float(cp.mean(data_gpu)),
                'std': float(cp.std(data_gpu)),
                'min': float(cp.min(data_gpu)),
                'max': float(cp.max(data_gpu)),
                'median': float(cp.median(data_gpu)),
                'p25': float(cp.percentile(data_gpu, 25)),
                'p75': float(cp.percentile(data_gpu, 75)),
                'p95': float(cp.percentile(data_gpu, 95))
            }
        else:
            stats = {
                'mean': float(np.mean(data)),
                'std': float(np.std(data)),
                'min': float(np.min(data)),
                'max': float(np.max(data)),
                'median': float(np.median(data)),
                'p25': float(np.percentile(data, 25)),
                'p75': float(np.percentile(data, 75)),
                'p95': float(np.percentile(data, 95))
            }
        return stats
    
    def clear_cache(self):
        """Clear GPU memory"""
        if self.gpu_available:
            mempool = cp.get_default_memory_pool()
            pinned_mempool = cp.get_default_pinned_memory_pool()
            mempool.free_all_blocks()
            pinned_mempool.free_all_blocks()


# ============================================================================
# CPU OPTIMIZER
# ============================================================================

class CPUOptimizer:
    """Multi-threading optimization for CPU"""
    
    def __init__(self, hardware: HardwareDetector):
        self.hardware = hardware
        self.max_workers = hardware.max_workers
    
    def parallel_simulations(self, func, num_simulations, **kwargs):
        """Run simulations in parallel across all CPU threads"""
        # Distribute work
        sims_per_worker = num_simulations // self.max_workers
        remaining = num_simulations % self.max_workers
        
        tasks = []
        for i in range(self.max_workers):
            count = sims_per_worker + (1 if i < remaining else 0)
            tasks.append((func, count, kwargs))
        
        # Execute in parallel
        results = []
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = [executor.submit(self._run_batch, task) for task in tasks]
            
            for future in as_completed(futures):
                try:
                    batch_results = future.result()
                    results.extend(batch_results)
                except Exception as e:
                    print(f"⚠️  Batch failed: {e}")
        
        return np.array(results)
    
    def _run_batch(self, task):
        """Run a batch of simulations"""
        func, count, kwargs = task
        return [func(**kwargs) for _ in range(count)]


# ============================================================================
# MONTE CARLO ENGINE
# ============================================================================

class MonteCarloEngine:
    """Hybrid CPU+GPU Monte Carlo simulation engine"""
    
    def __init__(self, hardware: HardwareDetector):
        self.hardware = hardware
        self.gpu = GPUAccelerator(hardware)
        self.cpu = CPUOptimizer(hardware)
    
    def simulate_investment(self, initial_amount: float, expected_return: float,
                           volatility: float, days: int, num_simulations: int = 10000):
        """
        Simulate investment outcomes
        
        Args:
            initial_amount: Starting investment ($)
            expected_return: Annual return (e.g., 0.10 for 10%)
            volatility: Annual volatility (e.g., 0.20 for 20%)
            days: Investment period in days
            num_simulations: Number of simulations
        """
        print(f"💰 Simulating {num_simulations:,} investment scenarios...")
        start = time.time()
        
        use_gpu = self.hardware.should_use_gpu(num_simulations)
        
        if use_gpu:
            print(f"   🎮 Using GPU: {self.hardware.specs['gpu']['name']}")
            results = self._simulate_investment_gpu(
                initial_amount, expected_return, volatility, days, num_simulations
            )
        else:
            print(f"   💻 Using CPU: {self.hardware.max_workers} threads")
            results = self._simulate_investment_cpu(
                initial_amount, expected_return, volatility, days, num_simulations
            )
        
        elapsed = time.time() - start
        print(f"   ✅ Complete in {elapsed:.2f}s ({num_simulations/elapsed:.0f} sims/sec)")
        
        return results
    
    def _simulate_investment_gpu(self, initial, ret, vol, days, num_sims):
        """GPU-accelerated investment simulation"""
        # Convert to daily
        daily_return = ret / 252
        daily_vol = vol / np.sqrt(252)
        
        # Generate random returns on GPU
        returns = self.gpu.generate_random_normal(
            shape=(num_sims, days),
            mean=daily_return,
            std=daily_vol
        )
        
        # Calculate cumulative returns
        cumulative = self.gpu.cumulative_product(1 + returns, axis=1, initial_value=initial)
        
        # Get final values
        final_values = cumulative[:, -1] if self.gpu.gpu_available else cumulative[:, -1]
        
        # Move to CPU
        results = self.gpu.to_cpu(final_values)
        self.gpu.clear_cache()
        
        return results
    
    def _simulate_investment_cpu(self, initial, ret, vol, days, num_sims):
        """CPU-optimized investment simulation"""
        daily_return = ret / 252
        daily_vol = vol / np.sqrt(252)
        
        def single_sim():
            returns = np.random.normal(daily_return, daily_vol, days)
            return initial * np.prod(1 + returns)
        
        return self.cpu.parallel_simulations(single_sim, num_sims)
    
    def simulate_binary_outcome(self, success_rate: float, success_value: float,
                                failure_value: float, num_simulations: int = 10000):
        """
        Simulate binary outcomes (success/failure)
        
        Example: Business success/failure
        """
        print(f"🎲 Simulating {num_simulations:,} binary outcomes...")
        start = time.time()
        
        use_gpu = self.hardware.should_use_gpu(num_simulations)
        
        if use_gpu:
            random_vals = self.gpu.to_gpu(np.random.random(num_simulations))
            successes = random_vals < success_rate
            results = self.gpu.to_cpu(
                successes * success_value + (~successes) * failure_value
            )
        else:
            def single_outcome():
                return success_value if np.random.random() < success_rate else failure_value
            
            results = self.cpu.parallel_simulations(single_outcome, num_simulations)
        
        elapsed = time.time() - start
        print(f"   ✅ Complete in {elapsed:.2f}s")
        
        return np.array(results)
    
    def simulate_job_change(self, current_salary: float, new_salary: float,
                           current_growth: float, new_growth: float,
                           current_risk: float, new_risk: float,
                           years: int = 5, num_simulations: int = 10000):
        """
        Simulate job change decision over multiple years
        
        Args:
            current_salary: Current annual salary
            new_salary: New job annual salary
            current_growth: Annual raise % (e.g., 0.03 for 3%)
            new_growth: New job annual raise %
            current_risk: Layoff probability (e.g., 0.05 for 5%)
            new_risk: New job layoff probability
            years: Simulation period
        """
        print(f"💼 Simulating {num_simulations:,} career paths over {years} years...")
        start = time.time()
        
        def single_career():
            current_total = 0
            new_total = 0
            current_employed = True   # track state — once laid off, stays off
            new_employed = True

            for year in range(years):
                # Check layoff this year (only if still employed)
                if current_employed and np.random.random() < current_risk:
                    current_employed = False

                if new_employed and np.random.random() < new_risk:
                    new_employed = False

                # Only earn if still employed
                if current_employed:
                    current_total += current_salary * ((1 + current_growth) ** year)

                if new_employed:
                    new_total += new_salary * ((1 + new_growth) ** year)

            return new_total - current_total
        
        results = self.cpu.parallel_simulations(single_career, num_simulations)
        
        elapsed = time.time() - start
        print(f"   ✅ Complete in {elapsed:.2f}s")
        
        return np.array(results)


# ============================================================================
# DECISION ANALYZER
# ============================================================================

class DecisionAnalyzer:
    """Analyzes simulation results and generates insights"""
    
    @staticmethod
    def analyze_results(results: np.ndarray, context: Dict = None) -> Dict:
        """
        Analyze simulation results
        
        Returns comprehensive statistics and insights
        """
        total = len(results)
        
        # Basic statistics
        stats = {
            'total_simulations': total,
            'mean': float(np.mean(results)),
            'median': float(np.median(results)),
            'std': float(np.std(results)),
            'min': float(np.min(results)),
            'max': float(np.max(results)),
            'range': float(np.max(results) - np.min(results))
        }
        
        # Percentiles
        stats['percentiles'] = {
            '5th': float(np.percentile(results, 5)),
            '25th': float(np.percentile(results, 25)),
            '50th': float(np.percentile(results, 50)),
            '75th': float(np.percentile(results, 75)),
            '95th': float(np.percentile(results, 95))
        }
        
        # Outcome distribution
        positive = np.sum(results > 0)
        negative = np.sum(results < 0)
        neutral = np.sum(results == 0)
        
        stats['outcomes'] = {
            'positive_count': int(positive),
            'negative_count': int(negative),
            'neutral_count': int(neutral),
            'positive_rate': float(positive / total),
            'negative_rate': float(negative / total),
            'success_rate': float(positive / total * 100)
        }
        
        # Risk metrics
        if stats['std'] > 0:
            stats['risk_metrics'] = {
                'coefficient_of_variation': float(stats['std'] / abs(stats['mean'])) if stats['mean'] != 0 else float('inf'),
                'sharpe_ratio': float(stats['mean'] / stats['std']) if stats['std'] > 0 else 0,
                'downside_risk': float(np.std(results[results < 0])) if negative > 0 else 0
            }
        
        # Value at Risk (VaR)
        stats['var'] = {
            'var_95': float(np.percentile(results, 5)),  # 95% confidence
            'var_99': float(np.percentile(results, 1))   # 99% confidence
        }
        
        return stats
    
    @staticmethod
    def generate_recommendation(stats: Dict, context: Dict = None) -> str:
        """
        Generate human-readable recommendation
        """
        success_rate = stats['outcomes']['success_rate']
        mean = stats['mean']
        risk = stats.get('risk_metrics', {}).get('coefficient_of_variation', 0)
        
        # PRIMARY signal: Expected Value
        # SECONDARY signal: Success rate (for risk-averse framing)
        if mean > 0 and success_rate >= 60:
            confidence = "HIGH"
            recommendation = "✅ RECOMMENDED"
            reason = f"Strong EV (${mean:,.0f}) with {success_rate:.1f}% success rate"
            
        elif mean > 0 and success_rate >= 40:
            confidence = "MEDIUM"
            recommendation = "⚠️  CAUTIOUSLY RECOMMENDED"
            reason = f"Positive EV (${mean:,.0f}) but only {success_rate:.1f}% success — high variance play"
            
        elif mean > 0 and success_rate < 40:
            confidence = "LOW"
            recommendation = "🎲 HIGH RISK / HIGH REWARD"
            reason = f"Positive EV (${mean:,.0f}) but {success_rate:.1f}% success — lottery-style odds"
            
        elif mean <= 0 and success_rate >= 60:
            confidence = "MEDIUM"
            recommendation = "⚠️  WEAK PASS"
            reason = f"High success rate ({success_rate:.1f}%) but negative EV (${mean:,.0f}) — check your assumptions"
            
        else:
            confidence = "HIGH"
            recommendation = "❌ NOT RECOMMENDED"
            reason = f"Negative EV (${mean:,.0f}) with only {success_rate:.1f}% success rate"
        
        # Risk assessment
        risk_level = "HIGH" if risk > 1.0 else "MEDIUM" if risk > 0.5 else "LOW"
        
        report = f"""
{'='*60}
🎯 QUANTUM DECISION ANALYSIS
{'='*60}

RECOMMENDATION: {recommendation}
CONFIDENCE: {confidence}

REASONING:
{reason}

KEY METRICS:
- Success Rate: {success_rate:.1f}%
- Expected Value: {mean:,.2f}
- Risk Level: {risk_level}
- Best Case: {stats['max']:,.2f}
- Worst Case: {stats['min']:,.2f}
- Median Outcome: {stats['median']:,.2f}

PROBABILITY DISTRIBUTION:
- Positive outcomes: {stats['outcomes']['positive_count']:,} ({stats['outcomes']['positive_rate']*100:.1f}%)
- Negative outcomes: {stats['outcomes']['negative_count']:,} ({stats['outcomes']['negative_rate']*100:.1f}%)

PERCENTILES:
- 95th percentile (optimistic): {stats['percentiles']['95th']:,.2f}
- 75th percentile: {stats['percentiles']['75th']:,.2f}
- 50th percentile (median): {stats['percentiles']['50th']:,.2f}
- 25th percentile: {stats['percentiles']['25th']:,.2f}
- 5th percentile (pessimistic): {stats['percentiles']['5th']:,.2f}

RISK ANALYSIS:
- Standard Deviation: {stats['std']:,.2f}
- Value at Risk (95%): {stats['var']['var_95']:,.2f}
- Value at Risk (99%): {stats['var']['var_99']:,.2f}

{'='*60}
"""
        return report


# ============================================================================
# VISUALIZATION ENGINE
# ============================================================================

class VisualizationEngine:
    """Creates visualizations of simulation results"""
    
    @staticmethod
    def create_distribution_plot(results: np.ndarray, title: str = "Outcome Distribution"):
        """Create distribution plot"""
        if not VISUALIZATION_AVAILABLE:
            print("⚠️  Visualization not available (install matplotlib & seaborn)")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 10))
        fig.suptitle(title, fontsize=16, fontweight='bold')
        
        # Histogram
        axes[0, 0].hist(results, bins=50, color='skyblue', edgecolor='black', alpha=0.7)
        axes[0, 0].axvline(np.mean(results), color='red', linestyle='--', label=f'Mean: {np.mean(results):.2f}')
        axes[0, 0].axvline(np.median(results), color='green', linestyle='--', label=f'Median: {np.median(results):.2f}')
        axes[0, 0].set_xlabel('Outcome Value')
        axes[0, 0].set_ylabel('Frequency')
        axes[0, 0].set_title('Histogram')
        axes[0, 0].legend()
        axes[0, 0].grid(True, alpha=0.3)
        
        # Box plot
        axes[0, 1].boxplot(results, vert=True)
        axes[0, 1].set_ylabel('Outcome Value')
        axes[0, 1].set_title('Box Plot')
        axes[0, 1].grid(True, alpha=0.3)
        
        # Cumulative distribution
        sorted_results = np.sort(results)
        cumulative = np.arange(1, len(sorted_results) + 1) / len(sorted_results)
        axes[1, 0].plot(sorted_results, cumulative, linewidth=2)
        axes[1, 0].set_xlabel('Outcome Value')
        axes[1, 0].set_ylabel('Cumulative Probability')
        axes[1, 0].set_title('Cumulative Distribution')
        axes[1, 0].grid(True, alpha=0.3)
        
        # Density plot
        axes[1, 1].hist(results, bins=50, density=True, alpha=0.6, color='blue', edgecolor='black')
        axes[1, 1].set_xlabel('Outcome Value')
        axes[1, 1].set_ylabel('Density')
        axes[1, 1].set_title('Probability Density')
        axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.show()
    
    @staticmethod
    def save_results(results: np.ndarray, stats: Dict, filename: str = "quantum_results.json"):
        """Save results to file"""
        output = {
            'timestamp': datetime.now().isoformat(),
            'statistics': stats,
            'raw_results': results.tolist()
        }
        
        with open(filename, 'w') as f:
            json.dump(output, f, indent=2)
        
        print(f"💾 Results saved to {filename}")


# ============================================================================
# MAIN QUANTUM SIMULATOR
# ============================================================================

class QuantumSimulator:
    """
    Main Quantum Decision Simulator
    
    Fully optimized for RTX 3050 + i5-12400F
    """
    
    def __init__(self, verbose: bool = True):
        """Initialize simulator"""
        self.hardware = HardwareDetector()
        self.monte_carlo = MonteCarloEngine(self.hardware)
        self.analyzer = DecisionAnalyzer()
        self.visualizer = VisualizationEngine()
        
        if verbose:
            self.hardware.print_info()
    
    def analyze_investment_decision(self, amount: float, asset: str = "stock",
                                   expected_return: float = 0.10, volatility: float = 0.20,
                                   time_horizon_days: int = 365, num_simulations: int = 10000,
                                   visualize: bool = False) -> Dict:
        """
        Analyze investment decision
        
        Args:
            amount: Investment amount ($)
            asset: Asset type (for context)
            expected_return: Annual expected return (0.10 = 10%)
            volatility: Annual volatility (0.20 = 20%)
            time_horizon_days: Investment period (days)
            num_simulations: Number of Monte Carlo simulations
            visualize: Show visualization plot
        
        Returns:
            Dictionary with analysis results
        """
        print(f"\n{'='*60}")
        print(f"💰 INVESTMENT DECISION ANALYSIS")
        print(f"{'='*60}")
        print(f"Asset: {asset}")
        print(f"Amount: ${amount:,.2f}")
        print(f"Expected Return: {expected_return*100:.1f}% annually")
        print(f"Volatility: {volatility*100:.1f}%")
        print(f"Time Horizon: {time_horizon_days} days ({time_horizon_days/365:.1f} years)")
        print(f"{'='*60}\n")
        
        # Run simulation
        results = self.monte_carlo.simulate_investment(
            initial_amount=amount,
            expected_return=expected_return,
            volatility=volatility,
            days=time_horizon_days,
            num_simulations=num_simulations
        )
        
        # Convert to gains/losses
        results = results - amount
        
        # Analyze
        stats = self.analyzer.analyze_results(results)
        recommendation = self.analyzer.generate_recommendation(stats)
        
        print(recommendation)
        
        # Visualize
        if visualize:
            self.visualizer.create_distribution_plot(
                results,
                title=f"{asset.title()} Investment: ${amount:,.0f} over {time_horizon_days} days"
            )
        
        return {
            'results': results,
            'statistics': stats,
            'recommendation': recommendation
        }
    
    def analyze_job_change(self, current_salary: float, new_salary: float,
                          current_growth: float = 0.03, new_growth: float = 0.05,
                          current_stability: float = 0.97, new_stability: float = 0.90,
                          years: int = 5, num_simulations: int = 10000,
                          visualize: bool = False) -> Dict:
        """
        Analyze job change decision
        
        Args:
            current_salary: Current annual salary ($)
            new_salary: New job annual salary ($)
            current_growth: Current job annual raise (0.03 = 3%)
            new_growth: New job annual raise (0.05 = 5%)
            current_stability: Current job security (0.97 = 97% safe)
            new_stability: New job security (0.90 = 90% safe)
            years: Simulation period
            num_simulations: Number of simulations
            visualize: Show plots
        """
        print(f"\n{'='*60}")
        print(f"💼 JOB CHANGE DECISION ANALYSIS")
        print(f"{'='*60}")
        print(f"Current Job: ${current_salary:,.0f}/year")
        print(f"New Job: ${new_salary:,.0f}/year")
        print(f"Time Horizon: {years} years")
        print(f"{'='*60}\n")
        
        # Run simulation
        results = self.monte_carlo.simulate_job_change(
            current_salary=current_salary,
            new_salary=new_salary,
            current_growth=current_growth,
            new_growth=new_growth,
            current_risk=1 - current_stability,
            new_risk=1 - new_stability,
            years=years,
            num_simulations=num_simulations
        )
        
        # Analyze
        stats = self.analyzer.analyze_results(results)
        recommendation = self.analyzer.generate_recommendation(stats)
        
        print(recommendation)
        
        # Visualize
        if visualize:
            self.visualizer.create_distribution_plot(
                results,
                title=f"Job Change: Net Benefit over {years} years"
            )
        
        return {
            'results': results,
            'statistics': stats,
            'recommendation': recommendation
        }
    
    def analyze_business_venture(self, investment: float, success_rate: float,
                                success_return: float, failure_loss_rate: float = 1.0,
                                num_simulations: int = 10000, visualize: bool = False) -> Dict:
        """
        Analyze business venture decision
        
        Args:
            investment: Initial investment ($)
            success_rate: Probability of success (0.60 = 60%)
            success_return: Return multiplier on success (3.0 = 3x investment)
            failure_loss_rate: Loss on failure (1.0 = lose all, 0.5 = lose half)
            num_simulations: Number of simulations
        """
        print(f"\n{'='*60}")
        print(f"🚀 BUSINESS VENTURE ANALYSIS")
        print(f"{'='*60}")
        print(f"Investment: ${investment:,.2f}")
        print(f"Success Rate: {success_rate*100:.1f}%")
        print(f"Success Return: {success_return}x investment")
        print(f"Failure Loss: {failure_loss_rate*100:.0f}% of investment")
        print(f"{'='*60}\n")
        
        # Calculate payoffs
        success_payoff = investment * (success_return - 1)  # Net gain
        failure_payoff = -investment * failure_loss_rate     # Net loss
        
        # Run simulation
        results = self.monte_carlo.simulate_binary_outcome(
            success_rate=success_rate,
            success_value=success_payoff,
            failure_value=failure_payoff,
            num_simulations=num_simulations
        )
        
        # Analyze
        stats = self.analyzer.analyze_results(results)
        recommendation = self.analyzer.generate_recommendation(stats)
        
        print(recommendation)
        
        # Visualize
        if visualize:
            self.visualizer.create_distribution_plot(
                results,
                title=f"Business Venture: ${investment:,.0f} investment"
            )
        
        return {
            'results': results,
            'statistics': stats,
            'recommendation': recommendation
        }
    
    def custom_decision(self, decision_name: str, simulation_func,
                       num_simulations: int = 10000, visualize: bool = False,
                       **kwargs) -> Dict:
        """
        Custom decision analysis
        
        Args:
            decision_name: Name of the decision
            simulation_func: Function that returns a single outcome
            num_simulations: Number of simulations
            visualize: Show plots
            **kwargs: Arguments to pass to simulation_func
        """
        print(f"\n{'='*60}")
        print(f"🎯 CUSTOM DECISION ANALYSIS: {decision_name}")
        print(f"{'='*60}\n")
        
        # Run simulation using CPU optimizer
        def single_sim():
            return simulation_func(**kwargs)
        
        results = self.monte_carlo.cpu.parallel_simulations(
            single_sim, num_simulations
        )
        
        # Analyze
        stats = self.analyzer.analyze_results(np.array(results))
        recommendation = self.analyzer.generate_recommendation(stats)
        
        print(recommendation)
        
        # Visualize
        if visualize:
            self.visualizer.create_distribution_plot(
                np.array(results),
                title=decision_name
            )
        
        return {
            'results': results,
            'statistics': stats,
            'recommendation': recommendation
        }
    
    def save_analysis(self, results: Dict, filename: str = "decision_analysis.json"):
        """Save analysis to file"""
        self.visualizer.save_results(
            results['results'],
            results['statistics'],
            filename
        )


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

if __name__ == "__main__":
    # Initialize
    qs = QuantumSimulator(verbose=True)
    
    print("\n🎮 TESTING QUANTUM SIMULATOR\n")
    
    # Test 1: Bitcoin Investment
    print("TEST 1: Should I invest $5000 in Bitcoin?")
    result1 = qs.analyze_investment_decision(
        amount=5000,
        asset="Bitcoin",
        expected_return=0.15,  # 15% annual return
        volatility=0.60,       # 60% volatility (very risky)
        time_horizon_days=365,
        num_simulations=10000,
        visualize=False
    )
    
    # Test 2: Job Change
    print("\n" + "="*60)
    print("TEST 2: Should I change jobs?")
    result2 = qs.analyze_job_change(
        current_salary=80000,
        new_salary=95000,
        current_growth=0.03,   # 3% raises
        new_growth=0.07,       # 7% raises
        current_stability=0.97, # 97% stable (3% layoff chance)
        new_stability=0.92,     # 92% stable (8% layoff chance)
        years=5,
        num_simulations=10000,
        visualize=False
    )
    
    # Test 3: Business Venture
    print("\n" + "="*60)
    print("TEST 3: Should I start a business?")
    result3 = qs.analyze_business_venture(
        investment=50000,
        success_rate=0.40,      # 40% success rate
        success_return=5.0,     # 5x return on success
        failure_loss_rate=0.80, # Lose 80% on failure
        num_simulations=10000,
        visualize=False
    )
    
    print("\n" + "="*60)
    print("✅ ALL TESTS COMPLETE")
    print("="*60)
