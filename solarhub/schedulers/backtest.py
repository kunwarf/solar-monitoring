#!/usr/bin/env python3
"""
Rolling Backtest & Policy Auto-Tuning System

This module implements a lightweight backtesting system that compares actual performance
against alternative parameter sets to automatically tune policy parameters for optimal
reliability and self-sufficiency.
"""

import logging
import json
import math
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path
import sqlite3

log = logging.getLogger(__name__)

@dataclass
class BacktestScenario:
    """Alternative parameter set for backtesting."""
    name: str
    emergency_soc_threshold_pct: float
    critical_soc_threshold_pct: float
    base_buffer_pct: float
    outage_risk_buffer_pct: float
    forecast_uncertainty_buffer_pct: float
    night_load_variability_buffer_pct: float
    max_total_buffer_pct: float

@dataclass
class BacktestResult:
    """Result of a backtest scenario."""
    scenario_name: str
    date: str
    actual_night_survivability: bool  # Did we survive the night without blackout?
    actual_grid_kwh: float  # Actual grid energy used
    projected_night_survivability: bool  # Would this scenario have survived?
    projected_grid_kwh: float  # Projected grid energy under this scenario
    soc_at_sunset: float  # SOC at sunset
    soc_at_sunrise: float  # SOC at sunrise
    night_load_kwh: float  # Actual night load
    outage_events: int  # Number of outage events during the night
    performance_score: float  # Combined score (higher is better)

class BacktestManager:
    """
    Manages rolling backtests and policy auto-tuning.
    
    Compares actual performance against alternative parameter sets and automatically
    adjusts policy parameters within bounds for optimal performance.
    """
    
    def __init__(self, db_logger, config_manager):
        self.db_logger = db_logger
        self.config_manager = config_manager
        self.backtest_file = Path("backtest_results.json")
        self.results: List[BacktestResult] = []
        
        # Alternative scenarios to test
        self.scenarios = [
            BacktestScenario(
                name="conservative",
                emergency_soc_threshold_pct=25.0,
                critical_soc_threshold_pct=35.0,
                base_buffer_pct=5.0,
                outage_risk_buffer_pct=8.0,
                forecast_uncertainty_buffer_pct=3.0,
                night_load_variability_buffer_pct=2.0,
                max_total_buffer_pct=15.0
            ),
            BacktestScenario(
                name="balanced",
                emergency_soc_threshold_pct=20.0,
                critical_soc_threshold_pct=30.0,
                base_buffer_pct=3.0,
                outage_risk_buffer_pct=5.0,
                forecast_uncertainty_buffer_pct=2.0,
                night_load_variability_buffer_pct=1.0,
                max_total_buffer_pct=10.0
            ),
            BacktestScenario(
                name="aggressive",
                emergency_soc_threshold_pct=15.0,
                critical_soc_threshold_pct=25.0,
                base_buffer_pct=2.0,
                outage_risk_buffer_pct=3.0,
                forecast_uncertainty_buffer_pct=1.0,
                night_load_variability_buffer_pct=0.5,
                max_total_buffer_pct=6.0
            ),
            BacktestScenario(
                name="current",
                emergency_soc_threshold_pct=20.0,  # Will be updated with current config
                critical_soc_threshold_pct=30.0,
                base_buffer_pct=2.0,
                outage_risk_buffer_pct=5.0,
                forecast_uncertainty_buffer_pct=2.0,
                night_load_variability_buffer_pct=1.0,
                max_total_buffer_pct=10.0
            )
        ]
        
        # Load existing results
        self._load_backtest_results()
        
        # Update current scenario with actual config
        self._update_current_scenario()
    
    def _load_backtest_results(self):
        """Load existing backtest results from file."""
        if self.backtest_file.exists():
            try:
                with open(self.backtest_file, 'r') as f:
                    data = json.load(f)
                    self.results = [BacktestResult(**result) for result in data]
                log.info(f"Loaded {len(self.results)} backtest results")
            except Exception as e:
                log.warning(f"Failed to load backtest results: {e}")
                self.results = []
    
    def _save_backtest_results(self):
        """Save backtest results to file."""
        try:
            with open(self.backtest_file, 'w') as f:
                json.dump([asdict(result) for result in self.results], f, indent=2)
        except Exception as e:
            log.warning(f"Failed to save backtest results: {e}")
    
    def _update_current_scenario(self):
        """Update the current scenario with actual configuration values."""
        try:
            # Get current configuration
            current_config = self.config_manager.load_config()
            
            # Update current scenario
            current_scenario = next(s for s in self.scenarios if s.name == "current")
            
            # Handle both PolicyConfig object and dictionary cases
            if hasattr(current_config, 'smart') and hasattr(current_config.smart, 'policy'):
                smart_policy = current_config.smart.policy
                # Use getattr for PolicyConfig objects
                current_scenario.emergency_soc_threshold_pct = getattr(smart_policy, 'emergency_soc_threshold_grid_available_pct', 20.0)
                current_scenario.critical_soc_threshold_pct = getattr(smart_policy, 'critical_soc_threshold_grid_available_pct', 30.0)
            else:
                # Fallback to default values if policy not available
                current_scenario.emergency_soc_threshold_pct = 20.0
                current_scenario.critical_soc_threshold_pct = 30.0
            
            log.info(f"Updated current scenario with config values")
        except Exception as e:
            log.warning(f"Failed to update current scenario: {e}")
    
    def run_daily_backtest(self, date: datetime, actual_data: Dict[str, Any]) -> List[BacktestResult]:
        """
        Run backtest for a specific date comparing actual vs projected performance.
        
        Args:
            date: Date to backtest
            actual_data: Actual performance data for the day
            
        Returns:
            List of backtest results for each scenario
        """
        log.info(f"Running daily backtest for {date.strftime('%Y-%m-%d')}")
        
        # Extract actual performance data
        actual_soc_sunset = actual_data.get('soc_at_sunset', 0.0)
        actual_soc_sunrise = actual_data.get('soc_at_sunrise', 0.0)
        actual_grid_kwh = actual_data.get('grid_kwh', 0.0)
        actual_night_load_kwh = actual_data.get('night_load_kwh', 0.0)
        actual_outage_events = actual_data.get('outage_events', 0)
        
        # Determine actual night survivability
        actual_night_survivability = actual_soc_sunrise >= 20.0  # 20% emergency reserve
        
        results = []
        
        for scenario in self.scenarios:
            # Project performance under this scenario
            projected_result = self._project_scenario_performance(
                scenario, actual_data, actual_soc_sunset, actual_night_load_kwh
            )
            
            # Calculate performance score
            performance_score = self._calculate_performance_score(
                actual_night_survivability, actual_grid_kwh,
                projected_result['night_survivability'], projected_result['grid_kwh'],
                actual_outage_events
            )
            
            result = BacktestResult(
                scenario_name=scenario.name,
                date=date.strftime('%Y-%m-%d'),
                actual_night_survivability=actual_night_survivability,
                actual_grid_kwh=actual_grid_kwh,
                projected_night_survivability=projected_result['night_survivability'],
                projected_grid_kwh=projected_result['grid_kwh'],
                soc_at_sunset=actual_soc_sunset,
                soc_at_sunrise=actual_soc_sunrise,
                night_load_kwh=actual_night_load_kwh,
                outage_events=actual_outage_events,
                performance_score=performance_score
            )
            
            results.append(result)
            log.info(f"Scenario {scenario.name}: score={performance_score:.2f}, "
                    f"survivability={projected_result['night_survivability']}, "
                    f"grid_kwh={projected_result['grid_kwh']:.2f}")
        
        # Add results to history
        self.results.extend(results)
        
        # Keep only last 30 days of results
        cutoff_date = datetime.now(timezone.utc) - timedelta(days=30)
        self.results = [
            r for r in self.results 
            if datetime.strptime(r.date, '%Y-%m-%d') >= cutoff_date
        ]
        
        # Save results
        self._save_backtest_results()
        
        return results
    
    def _project_scenario_performance(self, scenario: BacktestScenario, actual_data: Dict[str, Any], 
                                    soc_at_sunset: float, night_load_kwh: float) -> Dict[str, Any]:
        """Project how a scenario would have performed."""
        
        # Calculate effective minimum SOC under this scenario
        effective_min_soc = 20.0 + scenario.base_buffer_pct  # Base 20% + buffer
        
        # Add outage risk buffer if there were outages
        if actual_data.get('outage_events', 0) > 0:
            effective_min_soc += scenario.outage_risk_buffer_pct
        
        # Add forecast uncertainty buffer if forecasts were poor
        if actual_data.get('forecast_accuracy', 1.0) < 0.8:
            effective_min_soc += scenario.forecast_uncertainty_buffer_pct
        
        # Add night load variability buffer if load was highly variable
        if actual_data.get('night_load_variability', 0.0) > 0.3:
            effective_min_soc += scenario.night_load_variability_buffer_pct
        
        # Cap at maximum buffer
        effective_min_soc = min(effective_min_soc, 20.0 + scenario.max_total_buffer_pct)
        
        # Project night survivability
        # If SOC at sunset was below effective minimum, we would have needed grid charging
        if soc_at_sunset < effective_min_soc:
            # Would have needed grid charging to reach effective minimum
            required_charge_kwh = (effective_min_soc - soc_at_sunset) / 100.0 * actual_data.get('battery_capacity_kwh', 10.0)
            projected_grid_kwh = max(0, required_charge_kwh)
            projected_night_survivability = True  # Grid charging would have prevented blackout
        else:
            # SOC was sufficient, check if we would have survived the night
            projected_soc_after_night = soc_at_sunset - (night_load_kwh / actual_data.get('battery_capacity_kwh', 10.0) * 100)
            projected_night_survivability = projected_soc_after_night >= 20.0  # 20% emergency reserve
            projected_grid_kwh = 0.0  # No grid charging needed
        
        return {
            'night_survivability': projected_night_survivability,
            'grid_kwh': projected_grid_kwh,
            'effective_min_soc': effective_min_soc
        }
    
    def _calculate_performance_score(self, actual_survivability: bool, actual_grid_kwh: float,
                                   projected_survivability: bool, projected_grid_kwh: float,
                                   outage_events: int) -> float:
        """Calculate performance score for a scenario (higher is better)."""
        
        # Base score components
        survivability_score = 100.0 if projected_survivability else 0.0
        self_sufficiency_score = max(0, 100.0 - projected_grid_kwh * 10)  # Penalty for grid usage
        reliability_bonus = 20.0 if outage_events == 0 else max(0, 20.0 - outage_events * 5)
        
        # Weighted combination
        total_score = (
            survivability_score * 0.6 +  # 60% weight on survivability
            self_sufficiency_score * 0.3 +  # 30% weight on self-sufficiency
            reliability_bonus * 0.1  # 10% weight on reliability
        )
        
        return total_score
    
    def analyze_performance_trends(self) -> Dict[str, Any]:
        """Analyze performance trends over the last 30 days."""
        if len(self.results) < 7:  # Need at least a week of data
            return {"status": "insufficient_data", "message": "Need at least 7 days of backtest data"}
        
        # Group results by scenario
        scenario_performance = {}
        for scenario in self.scenarios:
            scenario_results = [r for r in self.results if r.scenario_name == scenario.name]
            if scenario_results:
                avg_score = sum(r.performance_score for r in scenario_results) / len(scenario_results)
                survivability_rate = sum(1 for r in scenario_results if r.projected_night_survivability) / len(scenario_results)
                avg_grid_kwh = sum(r.projected_grid_kwh for r in scenario_results) / len(scenario_results)
                
                scenario_performance[scenario.name] = {
                    'avg_score': avg_score,
                    'survivability_rate': survivability_rate,
                    'avg_grid_kwh': avg_grid_kwh,
                    'data_points': len(scenario_results)
                }
        
        # Find best performing scenario
        best_scenario = max(scenario_performance.items(), key=lambda x: x[1]['avg_score'])
        
        return {
            "status": "analysis_complete",
            "scenario_performance": scenario_performance,
            "best_scenario": best_scenario[0],
            "best_score": best_scenario[1]['avg_score'],
            "recommendation": self._generate_recommendation(scenario_performance, best_scenario)
        }
    
    def _generate_recommendation(self, scenario_performance: Dict[str, Any], best_scenario: Tuple[str, Dict]) -> Dict[str, Any]:
        """Generate policy tuning recommendations."""
        best_name, best_perf = best_scenario
        current_perf = scenario_performance.get('current', {})
        
        # If best scenario is significantly better than current, recommend tuning
        if best_perf['avg_score'] > current_perf.get('avg_score', 0) + 10:
            return {
                "action": "tune_parameters",
                "target_scenario": best_name,
                "expected_improvement": best_perf['avg_score'] - current_perf.get('avg_score', 0),
                "reason": f"Scenario '{best_name}' shows {best_perf['avg_score']:.1f} vs current {current_perf.get('avg_score', 0):.1f}"
            }
        else:
            return {
                "action": "maintain_current",
                "reason": "Current parameters are performing well"
            }
    
    def auto_tune_parameters(self, recommendation: Dict[str, Any]) -> bool:
        """Automatically tune parameters based on backtest recommendations."""
        if recommendation.get('action') != 'tune_parameters':
            return False
        
        target_scenario_name = recommendation.get('target_scenario')
        target_scenario = next((s for s in self.scenarios if s.name == target_scenario_name), None)
        
        if not target_scenario:
            log.warning(f"Target scenario '{target_scenario_name}' not found")
            return False
        
        try:
            # Update configuration with new parameters
            config_updates = {
                'smart.policy.emergency_soc_threshold_grid_available_pct': target_scenario.emergency_soc_threshold_pct,
                'smart.policy.critical_soc_threshold_grid_available_pct': target_scenario.critical_soc_threshold_pct,
                'smart.policy.base_buffer_pct': target_scenario.base_buffer_pct,
                'smart.policy.outage_risk_buffer_pct': target_scenario.outage_risk_buffer_pct,
                'smart.policy.forecast_uncertainty_buffer_pct': target_scenario.forecast_uncertainty_buffer_pct,
                'smart.policy.night_load_variability_buffer_pct': target_scenario.night_load_variability_buffer_pct,
                'smart.policy.max_total_buffer_pct': target_scenario.max_total_buffer_pct
            }
            
            # Apply updates within bounds
            for key, value in config_updates.items():
                self.config_manager.update_config(key, value, source="backtest_auto_tuning")
            
            log.info(f"Auto-tuned parameters to scenario '{target_scenario_name}'")
            return True
            
        except Exception as e:
            log.error(f"Failed to auto-tune parameters: {e}")
            return False
    
    def get_backtest_summary(self) -> Dict[str, Any]:
        """Get summary of backtest results."""
        if not self.results:
            return {"status": "no_data", "message": "No backtest data available"}
        
        # Calculate summary statistics
        total_days = len(set(r.date for r in self.results))
        scenarios_tested = len(set(r.scenario_name for r in self.results))
        
        # Recent performance (last 7 days)
        recent_results = [r for r in self.results 
                         if datetime.strptime(r.date, '%Y-%m-%d') >= datetime.now(timezone.utc) - timedelta(days=7)]
        
        recent_survivability = sum(1 for r in recent_results if r.actual_night_survivability) / len(recent_results) if recent_results else 0
        recent_avg_grid = sum(r.actual_grid_kwh for r in recent_results) / len(recent_results) if recent_results else 0
        
        return {
            "status": "summary_available",
            "total_days_tested": total_days,
            "scenarios_tested": scenarios_tested,
            "recent_survivability_rate": recent_survivability,
            "recent_avg_grid_kwh": recent_avg_grid,
            "last_backtest_date": max(r.date for r in self.results) if self.results else None
        }
