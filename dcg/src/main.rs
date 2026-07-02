//! dcg — Destructive Command Guard CLI（spec §8.2）。
//!
//! 使い方: `dcg -- <command> [args...]`
//! 許可: 何も出力せず exit code 0。
//! 遮断: 理由と代替案を stderr に出力し exit code 2。

mod rules;

use std::env;
use std::path::PathBuf;
use std::process::ExitCode;

use rules::{evaluate, Verdict};

fn workspace_root() -> PathBuf {
    env::var("WORKSPACE_ROOT")
        .map(PathBuf::from)
        .unwrap_or_else(|_| env::current_dir().unwrap_or_else(|_| PathBuf::from(".")))
}

fn main() -> ExitCode {
    let mut args: Vec<String> = env::args().skip(1).collect();
    if args.first().map(String::as_str) == Some("--") {
        args.remove(0);
    }

    if args.is_empty() {
        eprintln!("dcg: usage: dcg -- <command> [args...]");
        return ExitCode::from(64); // EX_USAGE
    }

    match evaluate(&args, &workspace_root()) {
        Verdict::Allowed => ExitCode::SUCCESS,
        Verdict::Blocked(b) => {
            eprintln!("dcg: blocked by rule {}: {}", b.rule_id, b.reason);
            eprintln!("dcg: suggestion: {}", b.suggestion);
            ExitCode::from(2)
        }
    }
}
