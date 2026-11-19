// session-watch：一個 pane，列出 issue session 的 worktree、result.md 狀態與 session 的 TUI 狀態。
// 只給人看：畫面不進模型 context，盤點 session 的判定仍只讀 result.md 與 gh。
// 資料來自 <repo>/scripts/session-watch.py，所以要用 `claude --plugin-dir <repo>/mods/session-watch` 從 repo 載入。

const PANE = 'session-watch'
const INTERVAL_MS = 60_000

// 模組狀態：pane 開著才定時重抓
let isOpen = false
let isLoading = false
let wantsAnother = false
let repos = []
// 預設只看這個 checkout 的 session 派出去的（腳本從這個 session 與同一個專案目錄的其他 session 的 jsonl 查
// orca worktree create 的回傳，接手的新 session 才看得到前一任派出去的）；
// 查不到派出紀錄就退到這個 session 所在 repo 底下。/session-watch all 看整台
let cwd = ''
let isAll = false
let data = { generated_at: '-', scope: '', rows: [], errors: [] }
let failure = ''

// attention 代碼 → 行首記號與顏色
const MARK = {
  input: { mark: '⏸', color: 'red' },
  you: { mark: '●', color: 'yellow' },
  nosession: { mark: '✕', color: 'red' },
  check: { mark: '?', color: 'magenta' },
  done: { mark: '✓', color: 'green' },
  '': { mark: '·', color: undefined },
}

// 各欄自己的顏色：一眼分得出哪段是 result.md 狀態、哪段是 session 的 TUI 狀態
const STATUS_COLOR = {
  working: 'cyan',
  'awaiting verification': 'blue',
  blocked: 'red',
  'ready for authorization': 'yellow',
  merged: 'green',
  unknown: 'magenta',
}
const SESSION_COLOR = { working: 'green', turn: 'green', sub: 'cyan', idle: 'yellow' }

const SCOPE = { dispatched: '這個 checkout 派出的', under: '這個 repo 底下', all: '整台', repos: '指定 repo' }

export function sessionText(row) {
  return row.session ? row.session.state + ' ' + row.session.silent : 'no session'
}

export function detail(row) {
  const parts = []
  if (row.note) parts.push(row.note)
  if (row.pending && !['無', '-', '—'].includes(row.pending)) parts.push('待你：' + row.pending)
  if (row.blocker && !['無', '-', '—'].includes(row.blocker)) parts.push('卡在：' + row.blocker)
  return parts.join(' ｜ ')
}

async function refresh($) {
  if (isLoading) {
    // 這輪抓完再補跑一次，剛換的 repo 才不會等到下一分鐘
    wantsAnother = true
    return
  }
  isLoading = true
  try {
    const argv = ['python3', $.plugin.root + '/../../scripts/session-watch.py', '--json']
    for (const r of repos) argv.push('--repo', r)
    if (!repos.length && !isAll) {
      // 每輪重取：/clear、/resume 會換 session id，而 session.start 不會再觸發
      const sessionId = (await $.session.id()) || ''
      if (sessionId) argv.push('--dispatched-by', sessionId)
      if (cwd) argv.push('--under', cwd)
    }
    // 腳本逐個 repo 查 git 與 gh，預設 30 秒不夠
    const out = await $.process.run(argv, { timeoutMs: 120_000 })
    if (out.exitCode !== 0) throw new Error((out.stderr || out.stdout || 'exit ' + out.exitCode).trim().split('\n').pop())
    data = JSON.parse(out.stdout)
    failure = ''
  } catch (err) {
    // 抓不到就保留上一輪的列，只在標題列說明
    failure = String((err && err.message) || err)
  } finally {
    isLoading = false
    $.ui.invalidate('ui.render')
    if (wantsAnother) {
      wantsAnother = false
      await refresh($)
    }
  }
}

export function register(on) {
  on('session.start', async ($, e, next) => {
    cwd = e.cwd || ''
    await $.command.register({
      name: 'session-watch',
      description: '開啟 issue session 監看 pane（預設只看這個 checkout 的 session 派出的；all 看整台；可接 repo 路徑；close 關閉）',
      argumentHint: '[repo 路徑… | all | auto | close]',
      immediate: true,
    })
    $.clock.every(INTERVAL_MS, async () => {
      if (isOpen) await refresh($)
    })
    return next(e)
  })

  on('command.run', { command: 'session-watch' }, async ($, e) => {
    const args = (e.args || '').trim()
    if (args === 'close') {
      // isOpen 由下面的 ui.close hook 設回 false，跟使用者自己關 pane 走同一條路
      await $.ui.close({ id: PANE })
      return {}
    }
    if (args === 'auto' || args === 'all') {
      repos = []
      isAll = args === 'all'
    } else if (args) repos = args.split(/\s+/)
    isOpen = true
    await $.ui.open({ id: PANE, title: 'Sessions', focus: true })
    await refresh($)
    return {}
  })

  // 使用者自己關掉 pane（Ctrl+X 再 X）時也要停抓，否則每分鐘白跑 git 與 gh
  on('ui.close', async ($, e, next) => {
    if (e.id === PANE) isOpen = false
    return next(e)
  })

  on('ui.render', { component: 'Pane' }, async ($, e, next) => {
    if (e.requestId !== PANE) return next(e)
    const { Box, Text, Button } = $.ui.resolve(e)

    const head = Box({
      flexDirection: 'row',
      columnGap: 2,
      children: [
        Text({ dimColor: true, children: ['更新 ' + data.generated_at + (isLoading ? ' …' : '')] }),
        Text({ dimColor: true, children: [data.rows.length + ' 個 worktree'] }),
        Text({ dimColor: true, children: [SCOPE[data.scope] || ''] }),
        Button({ key: 'refresh', label: '重新整理', hotkey: 'r', plain: true, onPress: () => refresh($) }),
      ],
    })

    const rows = data.rows.flatMap((row, i) => {
      const m = MARK[row.attention] || MARK['']
      const colored = (key, text, color, more) =>
        Text({ key, ...(color ? { color } : {}), ...more, children: [text] })
      const line = Box({
        key: 'row-' + i,
        flexDirection: 'row',
        columnGap: 2,
        children: [
          colored('mark', m.mark, m.color),
          colored('name', row.name, undefined, { bold: true, wrap: 'truncate-end' }),
          colored('status', row.status, STATUS_COLOR[row.status]),
          row.session
            ? colored('session', sessionText(row), SESSION_COLOR[row.session.state], { dimColor: row.session.state === 'quiet' })
            : colored('session', sessionText(row), 'red'),
          colored('pr', 'PR ' + row.pr, undefined, { dimColor: true }),
        ],
      })
      const d = detail(row)
      return d
        ? [line, Text({ key: 'detail-' + i, ...(m.color ? { color: m.color } : { dimColor: true }), wrap: 'truncate-end', children: ['   ' + d] })]
        : [line]
    })

    const notes = [...(failure ? ['讀取失敗：' + failure] : []), ...data.errors].map((t, i) =>
      Text({ key: 'err-' + i, color: 'red', wrap: 'truncate-end', children: [t] }),
    )
    const empty = data.rows.length === 0 && !isLoading ? [Text({ dimColor: true, children: ['沒有 issue session 的 worktree'] })] : []

    return Box({ flexDirection: 'column', children: [head, ...notes, ...rows, ...empty] })
  })
}
