import os
import re
import sys
import glob
import argparse
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# Configuração para gerar gráficos sem interface gráfica
plt.switch_backend('Agg')

def parse_filename_metadata(filename):
    """
    Extrai metadados do nome do ficheiro CSV.
    Exemplo: seed_18_follow_on_gain_1.5_noise_0.2_source_both_avoid_on.csv
    """
    base = os.path.basename(filename)
    
    seed_match = re.search(r'seed_(\d+)', base)
    follow_match = re.search(r'follow_(on|off)', base)
    gain_match = re.search(r'gain_([\d\.]+)', base)
    noise_match = re.search(r'noise_([\d\.]+)', base)
    source_match = re.search(r'source_([a-zA-Z0-9]+)', base)
    avoid_match = re.search(r'avoid_(on|off)', base)
    
    return {
        'filename': base,
        'seed': int(seed_match.group(1)) if seed_match else -1,
        'follow': follow_match.group(1) if follow_match else 'unknown',
        'gain': float(gain_match.group(1)) if gain_match else 0.0,
        'noise': float(noise_match.group(1)) if noise_match else 0.0,
        'source': source_match.group(1) if source_match else 'none',
        'avoid': avoid_match.group(1) if avoid_match else 'unknown'
    }

def analyze_csv_file(filepath):
    """
    Lê um ficheiro CSV e calcula métricas de seguimento, erro e eventos.
    """
    df = pd.read_csv(filepath)
    meta = parse_filename_metadata(filepath)
    
    required_cols = ['simulation_time', 'robot_id', 'following', 'angular_error', 'target_losses', 'collision_avoidance', 'x', 'y']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"A coluna '{col}' falta no ficheiro {filepath}")
            
    time_steps = sorted(df['simulation_time'].unique())
    dt = np.mean(np.diff(time_steps)) if len(time_steps) > 1 else 0.032
    total_sim_time = time_steps[-1] - time_steps[0] if len(time_steps) > 1 else df['simulation_time'].max()
    
    robots = df['robot_id'].unique()
    num_robots = len(robots)
    
    following_times = []
    following_pcts = []
    angular_errors_deg = []
    
    for r_id in robots:
        rdf = df[df['robot_id'] == r_id].sort_values('simulation_time')
        f_rows = rdf[rdf['following'] == 1]
        f_time = len(f_rows) * dt
        f_pct = (f_time / total_sim_time) * 100.0 if total_sim_time > 0 else 0.0
        
        following_times.append(f_time)
        following_pcts.append(f_pct)
        
        valid_errs = f_rows['angular_error'].dropna()
        if len(valid_errs) > 0:
            err_deg = np.abs(valid_errs) * (180.0 / np.pi)
            angular_errors_deg.extend(err_deg.tolist())
            
    avg_following_time = np.mean(following_times)
    avg_following_pct = np.mean(following_pcts)
    
    mean_ang_err_deg = np.mean(angular_errors_deg) if len(angular_errors_deg) > 0 else np.nan
    std_ang_err_deg = np.std(angular_errors_deg) if len(angular_errors_deg) > 0 else np.nan
    
    target_losses_count = df.groupby('robot_id')['target_losses'].max().sum()
    collision_count = df.groupby('robot_id')['collision_avoidance'].max().sum()
    
    metrics = {
        **meta,
        'num_robots': num_robots,
        'sim_duration_s': total_sim_time,
        'avg_following_time_s': avg_following_time,
        'avg_following_pct': avg_following_pct,
        'mean_angular_error_deg': mean_ang_err_deg,
        'std_angular_error_deg': std_ang_err_deg,
        'total_target_losses': int(target_losses_count),
        'total_collisions': int(collision_count)
    }
    
    return metrics, df

def plot_trajectories(df, filepath_out, title="Multi-Robot Trajectories (Webots Arena)"):
    """
    Gera gráfico 2D das trajetórias na arena de 6x6 m.
    """
    plt.figure(figsize=(6, 6), dpi=300)
    robots = sorted(df['robot_id'].unique())
    colors = plt.cm.tab10(np.linspace(0, 1, max(10, len(robots))))
    
    for idx, r_id in enumerate(robots):
        rdf = df[df['robot_id'] == r_id].sort_values('simulation_time')
        x, y = rdf['x'].values, rdf['y'].values
        c = colors[idx]
        
        plt.plot(x, y, label=r_id, color=c, linewidth=1.8, alpha=0.85)
        plt.plot(x[0], y[0], marker='o', markersize=6, color=c, markeredgecolor='black')
        plt.plot(x[-1], y[-1], marker='X', markersize=8, color=c, markeredgecolor='black')

    plt.plot([-3, 3, 3, -3, -3], [-3, -3, 3, 3, -3], 'k--', linewidth=1.2, label='Arena (6x6m)')
    plt.title(title, fontsize=11, fontweight='bold', pad=10)
    plt.xlabel('Posição X [m]', fontsize=10)
    plt.ylabel('Posição Y [m]', fontsize=10)
    plt.xlim(-3.5, 3.5)
    plt.ylim(-3.5, 3.5)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.axis('equal')
    plt.legend(loc='upper right', fontsize=8)
    plt.tight_layout()
    plt.savefig(filepath_out)
    plt.close()

def generate_latex_table(df_summary):
    """
    Gera o código LaTeX da Tabela de Resultados para o IEEE.
    """
    latex = [
        "\\begin{table}[htbp]",
        "\\caption{Experimental Performance Evaluation Across Test Configurations}",
        "\\label{tab:experimental_results}",
        "\\centering",
        "\\begin{tabular}{lcccc}",
        "\\hline",
        "\\textbf{Configuration} & \\textbf{Follow Dur. (s)} & \\textbf{Ang. Error ($^\\circ$)} & \\textbf{Target Losses} & \\textbf{Collisions} \\\\",
        "\\hline"
    ]
    
    grouped = df_summary.groupby(['follow', 'gain', 'noise', 'source', 'avoid'])
    for (follow, gain, noise, source, avoid), group in grouped:
        f_dur_mean = group['avg_following_time_s'].mean()
        f_dur_std = group['avg_following_time_s'].std() if len(group) > 1 else 0.0
        
        err_mean = group['mean_angular_error_deg'].mean()
        err_std = group['std_angular_error_deg'].mean() if len(group) > 1 else 0.0
        
        losses = group['total_target_losses'].sum()
        collisions = group['total_collisions'].sum()
        
        cfg_str = f"Follow {follow}, Gain {gain}, Noise {noise} ({source}), Avoid {avoid}".replace('_', '\\_')
        err_str = f"{err_mean:.2f}$^\\circ$ $\\pm$ {err_std:.2f}$^\\circ$" if not np.isnan(err_mean) else "N/A"
        
        latex.append(f"{cfg_str} & {f_dur_mean:.2f} $\\pm$ {f_dur_std:.2f} & {err_str} & {losses} & {collisions} \\\\")
        
    latex.extend(["\\hline", "\\end{tabular}", "\\end{table}"])
    return "\n".join(latex)

def process_all_logs(results_dir, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    csv_files = glob.glob(os.path.join(results_dir, "*.csv"))
    
    if not csv_files:
        print(f"[!] Nenhum ficheiro CSV encontrado em: {results_dir}")
        return
        
    print(f"[*] A processar {len(csv_files)} ficheiros CSV em '{results_dir}'...")
    all_metrics = []
    
    for filepath in csv_files:
        try:
            metrics, df_raw = analyze_csv_file(filepath)
            all_metrics.append(metrics)
            
            base_name = os.path.basename(filepath).replace('.csv', '')
            plot_path = os.path.join(output_dir, f"plot_{base_name}.png")
            plot_trajectories(df_raw, plot_path, title=f"Trajetórias: {base_name}")
            print(f"  [+] Gráfico gerado: {plot_path}")
        except Exception as e:
            print(f"[!] Erro em {filepath}: {e}")
            
    df_summary = pd.DataFrame(all_metrics)
    df_summary.to_csv(os.path.join(output_dir, "summary_results.csv"), index=False)
    
    latex_code = generate_latex_table(df_summary)
    with open(os.path.join(output_dir, "table_results_IEEE.tex"), 'w') as f:
        f.write(latex_code)
        
    print("\n[+] Análise concluída! Resultados salvos em:", output_dir)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Processador de Logs CSV Webots/ROS 2")
    parser.add_argument('--input', type=str, default='~/Documents/RI/RI_Assesment1/experiments/results', help="Caminho dos CSVs")
    parser.add_argument('--output', type=str, default='./output_analysis', help="Pasta de saída")
    
    args = parser.parse_args()
    process_all_logs(os.path.expanduser(args.input), os.path.expanduser(args.output))
