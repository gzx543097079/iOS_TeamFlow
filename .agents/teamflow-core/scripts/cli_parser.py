"""命令行参数定义；业务行为由 teamflow 分派。"""
import argparse
from pathlib import Path
from requirement_model import STATES, BLOCK_KINDS

def build_parser():
    """命令行定义单独构建，供 validate_workflow 核对文档中的命令参数。"""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path('.'))
    output = argparse.ArgumentParser(add_help=False)
    output.add_argument('--json', action='store_true', help='输出完整结构化结果')
    top = parser.add_subparsers(dest='area', required=True)
    top.add_parser('doctor', parents=[output], help='只读核对接入、配置、需求证据和可选模块索引')
    permissions = top.add_parser('permissions', parents=[output], help='显式管理可选宿主审批模板')
    permissions.add_argument('--mode', choices=['default', 'strict'], required=True)
    permissions.add_argument('--plan', action='store_true')

    req = top.add_parser('req')
    req_sub = req.add_subparsers(dest='command', required=True)
    creator = req_sub.add_parser('create', parents=[output])
    creator.add_argument('--title', required=True)
    creator.add_argument('--queued', action='store_true', help='进行中但排队，暂不开始')
    creator.add_argument('--bug', action='store_true')
    req_sub.add_parser('list', parents=[output]).add_argument('--all', action='store_true', help='包含已完成和取消的需求')
    req_sub.add_parser('status', parents=[output], help='只读：状态、证据有效性、剩余 AC 与下一步').add_argument('requirement')
    req_sub.add_parser('pr', parents=[output], help='只读：由需求卡生成 PR 描述').add_argument('requirement')
    state = req_sub.add_parser('state', parents=[output])
    state.add_argument('requirement')
    state.add_argument('--state', choices=[s for s in STATES if s not in ('完成', '待用户验证')], required=True)
    state.add_argument('--blocked', choices=BLOCK_KINDS, help='阻塞原因类型')
    state.add_argument('--reason')
    state.add_argument('--reopen-ac', action='append', metavar='AC-编号',
                       help='重开完成的需求时取消勾选需重新验收的条件，可重复；须同时 --reason')
    done = req_sub.add_parser('complete', parents=[output])
    done.add_argument('requirement')
    proof = done.add_mutually_exclusive_group()
    proof.add_argument('--profile')
    proof.add_argument('--result')
    proof.add_argument('--evidence')
    done.add_argument('--rerun', action='store_true', help='与 --profile 一起显式重跑；默认复用有效证据')
    done.add_argument('--wait-user', action='store_true')
    done.add_argument('--evidence-input', action='append', help='人工核对的项目相对文件/目录，可重复；默认整个项目')
    done.add_argument('--confirm-ac', action='append', metavar='AC-编号',
                      help='显式确认已实际核对的条件，可重复传入；验证证据有效后才写入')
    done.add_argument('--user-confirmed', action='append', metavar='AC-编号',
                      help='用户已在对话中明确确认的条件；勾选并记入头部 user_confirmed')

    verify = top.add_parser('verify')
    verify_sub = verify.add_subparsers(dest='command', required=True)
    verify_sub.add_parser('init')
    verify_sub.add_parser('list')
    verify_sub.add_parser('suggest', parents=[output], help='按改动路径建议验证范围，不运行检查').add_argument(
        '--requirement', help='同时计入该需求带 Requirement 尾注的已提交改动')
    run = verify_sub.add_parser('run', parents=[output])
    run.add_argument('--profile', required=True)
    run.add_argument('--requirement', help='绑定本次需求的范围和 AC，忽略其他需求')
    run.add_argument('--rerun', action='store_true', help='强制执行所选 profile 全部检查，绕过增量缓存')

    git_area = top.add_parser('git')
    git_sub = git_area.add_subparsers(dest='command', required=True)
    check = git_sub.add_parser('check', parents=[output])
    check.add_argument('requirement')
    check.add_argument('--result')
    check.add_argument('--evidence')
    check.add_argument('--evidence-input', action='append')
    gate = git_sub.add_parser('hook', parents=[output], help='只读复核暂存证据，不执行测试')
    # 1.2 及更早的托管 Hook 会传入 --profile；仅为兼容旧 Hook 而接受，doctor 提示迁移。
    gate.add_argument('--profile', help=argparse.SUPPRESS)
    ci = git_sub.add_parser('ci', parents=[output], help='只读：核对基线之后改动的完成卡证据，供 CI 使用')
    ci.add_argument('--base', required=True, help='比较基线，如 origin/main')

    installer = top.add_parser('setup', help='接入或更新项目入口；可直接从 Skill 目录运行')
    installer.add_argument('--mode', choices=['ios', 'godot', 'godot-ios'],
                           help='安装 iOS 原生、Godot 或 Godot + iOS；省略时沿用已有选择，首次默认 ios')
    installer.add_argument('--plan', action='store_true', help='只输出待修改内容的 diff')
    installer.add_argument('--claude-skill-link', action='store_true',
                           help='为选中的安装模式创建 Claude Code Skill 软链接')
    hook = installer.add_mutually_exclusive_group()
    hook.add_argument('--git-hook', action='store_true', help='安装本机 pre-commit，提交前复核覆盖暂存内容的已绑定证据')
    hook.add_argument('--no-git-hook', action='store_true', help='移除 TeamFlow 管理的 pre-commit')

    installer_pkg = top.add_parser('install', parents=[output], help='从安装包一键接入（无需人工整包解压）')
    installer_pkg.add_argument('package', type=Path, help='teamflow-*-vX.Y.Z.zip')
    installer_pkg.add_argument('--mode', choices=['ios', 'godot', 'godot-ios'], default='ios',
                               help='安装模式；默认 ios')
    installer_pkg.add_argument('--plan', action='store_true', help='只读预览，不写文件')
    installer_pkg.add_argument('--force', action='store_true', help='覆盖已安装的核心与 Skill 后重新接入')

    upgrader = top.add_parser('upgrade', parents=[output], help='用新版安装包升级核心与所选 Skill')
    upgrader.add_argument('package', type=Path, help='新版安装包 ZIP')
    upgrader.add_argument('--plan', action='store_true', help='只读预览，不写文件')
    upgrader.add_argument('--force', action='store_true', help='覆盖本地改动')
    upgrader.add_argument('--mode', choices=['ios', 'godot', 'godot-ios'], help='升级同时切换安装模式；省略时沿用')

    module = top.add_parser('module', help='大型项目模块索引')
    module_sub = module.add_subparsers(dest='command', required=True)
    inspect = module_sub.add_parser('inspect', parents=[output], help='只读路由并列出模块增量')
    target = inspect.add_mutually_exclusive_group(required=True)
    target.add_argument('--query')
    target.add_argument('--module', action='append')
    target.add_argument('--all', action='store_true')
    module_sub.add_parser('validate', parents=[output], help='校验索引与全部模块路径')
    add = module_sub.add_parser('record', help='记录或更新一个模块')
    add.add_argument('--name', required=True)
    add.add_argument('--responsibility')
    add.add_argument('--trigger', action='append', required=True)
    add.add_argument('--path', action='append', required=True)
    add.add_argument('--entry', action='append', default=[])
    add.add_argument('--dependency', action='append', default=[])
    add.add_argument('--caller', action='append', default=[])
    add.add_argument('--verification', action='append', default=[])
    add.add_argument('--cross-cutting', action='append', default=[])

    logging_area = top.add_parser('logging', help='原生日志组件')
    logging_sub = logging_area.add_subparsers(dest='command', required=True)
    install = logging_sub.add_parser('install', parents=[output], help='按工程语言复制日志源码到业务目录')
    install.add_argument('--destination', required=True)
    install.add_argument('--language', choices=('swift', 'objc', 'mixed'), required=True)
    return parser

