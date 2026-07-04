//! dcg のルール判定ロジック — spec §8.2。
//!
//! 3段解析:
//!   1. Quick Reject: トリガーとなるトークンが argv に一つも無ければ即通過。
//!   2. Context Classification: argv はシェルが分割済みのトークン列なので、
//!      「rm -rf」という文字列がコミットメッセージ等の1トークン内に埋め込まれていても、
//!      それは "rm" と "-rf" という2つの独立したトークンとして argv に現れない限り
//!      危険なコマンドとして判定されない（誤検知ゼロ）。
//!   3. 遮断: ルールに一致したら Verdict::Blocked を返す（呼び出し側で exit code 2 にする）。

use std::path::{Path, PathBuf};

#[derive(Debug, Clone, PartialEq, Eq)]
pub struct Blocked {
    pub rule_id: &'static str,
    pub reason: String,
    pub suggestion: String,
}

#[derive(Debug, Clone, PartialEq, Eq)]
pub enum Verdict {
    Allowed,
    Blocked(Blocked),
}

const TRIGGER_TOKENS: &[&str] = &[
    "rm", "reset", "push", "dd", "mkfs", "fdisk",
];

/// Quick Reject: いずれのトリガートークンもargvに存在しなければ即座に許可する。
fn quick_reject_passes(argv: &[String]) -> bool {
    !argv.iter().any(|tok| {
        TRIGGER_TOKENS.contains(&tok.as_str()) || tok.starts_with("mkfs")
    })
}

fn has_flag(argv: &[String], long: &str, short: &str) -> bool {
    argv.iter().any(|a| a == long || a == short)
}

fn contains_rf_flag(argv: &[String]) -> bool {
    argv.iter().any(|a| {
        let a = a.as_str();
        matches!(a, "-rf" | "-fr" | "-r" | "-R" | "--recursive")
            && has_flag(argv, "--force", "-f")
    }) || argv.iter().any(|a| matches!(a.as_str(), "-rf" | "-fr"))
}

/// core.filesystem: `rm -rf` は ${WORKSPACE_ROOT}/tmp 配下のみ許可。
fn check_rm(argv: &[String], workspace_root: &Path) -> Option<Blocked> {
    if argv.first().map(String::as_str) != Some("rm") {
        return None;
    }
    if !contains_rf_flag(argv) {
        return None;
    }
    let tmp_root = workspace_root.join("tmp");
    let targets: Vec<&String> = argv[1..].iter().filter(|a| !a.starts_with('-')).collect();

    if targets.is_empty() {
        return Some(Blocked {
            rule_id: "core.filesystem",
            reason: "rm -rf に削除対象が指定されていません（危険なため遮断）。".to_string(),
            suggestion: format!("{} 配下のパスを明示的に指定してください。", tmp_root.display()),
        });
    }

    let all_within_tmp = targets.iter().all(|t| {
        let candidate = PathBuf::from(t);
        let resolved = if candidate.is_absolute() {
            candidate
        } else {
            workspace_root.join(candidate)
        };
        resolved.starts_with(&tmp_root)
    });

    if all_within_tmp {
        None
    } else {
        Some(Blocked {
            rule_id: "core.filesystem",
            reason: "システムルート/管理外への rm -rf は遮断されます。".to_string(),
            suggestion: format!(
                "{} 配下のみ削除が許可されています。",
                tmp_root.display()
            ),
        })
    }
}

/// core.git: `git reset --hard` は未コミット変更の喪失リスク。
fn check_git_reset_hard(argv: &[String]) -> Option<Blocked> {
    if argv.first().map(String::as_str) != Some("git") {
        return None;
    }
    let has_reset = argv.iter().any(|a| a == "reset");
    let has_hard = argv.iter().any(|a| a == "--hard");
    if has_reset && has_hard {
        Some(Blocked {
            rule_id: "core.git",
            reason: "git reset --hard は未コミット変更を失うリスクがあります。".to_string(),
            suggestion: "git stash を使い、変更を退避してください。".to_string(),
        })
    } else {
        None
    }
}

/// core.git:force-push: main/master への --force は上書きリスク。
fn check_git_force_push(argv: &[String]) -> Option<Blocked> {
    if argv.first().map(String::as_str) != Some("git") {
        return None;
    }
    let has_push = argv.iter().any(|a| a == "push");
    let has_force = argv.iter().any(|a| a == "--force" || a == "-f");
    if !has_push || !has_force {
        return None;
    }

    let targets_protected_branch = argv.iter().any(|a| {
        let a = a.as_str();
        a == "main"
            || a == "master"
            || a.ends_with(":main")
            || a.ends_with(":master")
            || a.ends_with("/main")
            || a.ends_with("/master")
    });

    // 明示的にリモート/ブランチを指定していない場合（現在のブランチをpush）は
    // それがmain/masterである可能性を排除できないため、安全側に倒して遮断する。
    let has_explicit_non_main_target = argv.iter().skip_while(|a| a.as_str() != "push").skip(1).any(|a| {
        !a.starts_with('-') && a != "main" && a != "master"
    });

    if targets_protected_branch || !has_explicit_non_main_target {
        Some(Blocked {
            rule_id: "core.git:force-push",
            reason: "main/master への git push --force は強制上書きのリスクがあります。".to_string(),
            suggestion: "--force-with-lease への置き換えを検討してください。".to_string(),
        })
    } else {
        None
    }
}

/// system.disk: dd/mkfs/fdisk は物理デバイス対象のためハードブロック（代替提案なし）。
fn check_disk_tools(argv: &[String]) -> Option<Blocked> {
    let cmd = argv.first().map(String::as_str).unwrap_or("");
    if cmd == "dd" || cmd == "fdisk" || cmd.starts_with("mkfs") {
        Some(Blocked {
            rule_id: "system.disk",
            reason: format!("{cmd} は物理デバイスを対象にしうるため実行できません。"),
            suggestion: "代替手段はありません（ハードブロック）。".to_string(),
        })
    } else {
        None
    }
}

pub fn evaluate(argv: &[String], workspace_root: &Path) -> Verdict {
    if argv.is_empty() {
        return Verdict::Allowed;
    }

    // ① Quick Reject
    if quick_reject_passes(argv) {
        return Verdict::Allowed;
    }

    // ② Context Classification は argv がトークン列である時点で自然に満たされる
    //    （コミットメッセージ等のフリーテキストは1トークンにまとまっているため、
    //    "rm"/"-rf" のような複数トークンの一致とは判定されない）。

    // ③ ルール判定
    if let Some(b) = check_disk_tools(argv) {
        return Verdict::Blocked(b);
    }
    if let Some(b) = check_rm(argv, workspace_root) {
        return Verdict::Blocked(b);
    }
    if let Some(b) = check_git_reset_hard(argv) {
        return Verdict::Blocked(b);
    }
    if let Some(b) = check_git_force_push(argv) {
        return Verdict::Blocked(b);
    }

    Verdict::Allowed
}

#[cfg(test)]
mod tests {
    use super::*;

    fn argv(s: &[&str]) -> Vec<String> {
        s.iter().map(|x| x.to_string()).collect()
    }

    fn root() -> PathBuf {
        PathBuf::from("/workspace")
    }

    #[test]
    fn allows_harmless_commands() {
        assert_eq!(evaluate(&argv(&["ls", "-la"]), &root()), Verdict::Allowed);
        assert_eq!(evaluate(&argv(&["git", "status"]), &root()), Verdict::Allowed);
        assert_eq!(evaluate(&argv(&["npm", "install"]), &root()), Verdict::Allowed);
    }

    #[test]
    fn blocks_rm_rf_outside_tmp() {
        let v = evaluate(&argv(&["rm", "-rf", "/"]), &root());
        match v {
            Verdict::Blocked(b) => assert_eq!(b.rule_id, "core.filesystem"),
            _ => panic!("expected blocked"),
        }
    }

    #[test]
    fn allows_rm_rf_inside_workspace_tmp() {
        let v = evaluate(&argv(&["rm", "-rf", "/workspace/tmp/scratch"]), &root());
        assert_eq!(v, Verdict::Allowed);
    }

    #[test]
    fn blocks_rm_rf_with_no_target() {
        let v = evaluate(&argv(&["rm", "-rf"]), &root());
        match v {
            Verdict::Blocked(b) => assert_eq!(b.rule_id, "core.filesystem"),
            _ => panic!("expected blocked"),
        }
    }

    #[test]
    fn blocks_git_reset_hard() {
        let v = evaluate(&argv(&["git", "reset", "--hard", "HEAD~1"]), &root());
        match v {
            Verdict::Blocked(b) => assert_eq!(b.rule_id, "core.git"),
            _ => panic!("expected blocked"),
        }
    }

    #[test]
    fn allows_git_reset_soft() {
        let v = evaluate(&argv(&["git", "reset", "--soft", "HEAD~1"]), &root());
        assert_eq!(v, Verdict::Allowed);
    }

    #[test]
    fn blocks_force_push_to_main() {
        let v = evaluate(&argv(&["git", "push", "--force", "origin", "main"]), &root());
        match v {
            Verdict::Blocked(b) => assert_eq!(b.rule_id, "core.git:force-push"),
            _ => panic!("expected blocked"),
        }
    }

    #[test]
    fn blocks_force_push_with_no_explicit_branch() {
        // ブランチ省略（現在のブランチをpush）は main である可能性を排除できないため遮断。
        let v = evaluate(&argv(&["git", "push", "--force"]), &root());
        match v {
            Verdict::Blocked(b) => assert_eq!(b.rule_id, "core.git:force-push"),
            _ => panic!("expected blocked"),
        }
    }

    #[test]
    fn allows_force_push_to_feature_branch() {
        let v = evaluate(
            &argv(&["git", "push", "--force", "origin", "feature/foo"]),
            &root(),
        );
        assert_eq!(v, Verdict::Allowed);
    }

    #[test]
    fn allows_force_with_lease() {
        let v = evaluate(
            &argv(&["git", "push", "--force-with-lease", "origin", "main"]),
            &root(),
        );
        assert_eq!(v, Verdict::Allowed);
    }

    #[test]
    fn blocks_disk_tools_hard() {
        for cmd in ["dd", "fdisk", "mkfs.ext4"] {
            let v = evaluate(&argv(&[cmd, "/dev/sda"]), &root());
            match v {
                Verdict::Blocked(b) => assert_eq!(b.rule_id, "system.disk"),
                _ => panic!("expected blocked for {cmd}"),
            }
        }
    }

    #[test]
    fn commit_message_mentioning_rm_rf_is_not_blocked() {
        // §15.3: コミットメッセージ内の "rm -rf" 等テキストは誤遮断しない（False Positive ゼロ）。
        let v = evaluate(
            &argv(&["git", "commit", "-m", "fix: remove rm -rf usage from script"]),
            &root(),
        );
        assert_eq!(v, Verdict::Allowed);
    }

    #[test]
    fn commit_message_mentioning_force_push_is_not_blocked() {
        let v = evaluate(
            &argv(&["git", "commit", "-m", "docs: explain git push --force danger"]),
            &root(),
        );
        assert_eq!(v, Verdict::Allowed);
    }
}
