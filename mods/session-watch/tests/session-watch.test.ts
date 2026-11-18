import { expect, mock, test } from 'claude-code/testing'

const PANE = {
  plugin: 'session-watch',
  component: 'Pane',
  requestId: 'session-watch',
  viewport: { columns: 120, rows: 40 },
  props: {
    title: 'Sessions',
    isFocused: true,
    bodyColumns: 60,
    placement: 'inline',
    scroll: { offset: 0, bodyRows: 10 },
    view: {},
  },
} as const

const row = (over: Record<string, unknown>) => ({
  name: 'widgets/issue-1',
  status: 'working',
  attention: '',
  note: '',
  session: { name: 's', state: 'working', silent: '0m05s' },
  pr: '-',
  pending: '無',
  blocker: '無',
  ...over,
})

function stubs(on: any, payload: () => unknown) {
  const calls: string[][] = []
  on('session.start', () => ({ cwd: '/tmp/widgets' }))
  let sid = 0
  on('session.id', () => ({ value: 'sid-' + ++sid }))
  on('command.register', () => ({ value: undefined }))
  on('ui.open', () => ({ value: { isPlaced: true } }))
  on('ui.close', () => ({ value: undefined }))
  on('process.run', ($: unknown, e: any) => {
    calls.push(e.argv)
    const p = payload()
    return { value: typeof p === 'string' ? { exitCode: 1, stdout: '', stderr: p } : { exitCode: 0, stdout: JSON.stringify(p), stderr: '' } }
  })
  return calls
}

test('the pane lists rows and flags a session waiting for input', async ($, on) => {
  mock.clock(on)
  stubs(on, () => ({
    generated_at: '10:00',
    scope: 'dispatched',
    errors: [],
    rows: [
      row({ name: 'widgets/issue-2', attention: 'input', note: 'session 停在等你輸入', session: { name: 's', state: 'idle', silent: '12m00s' } }),
      row({}),
    ],
  }))
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/tmp/widgets' })
  await $.command.run({ command: 'session-watch', args: '' })
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /^這個 session 派出的$/ })).toBeDefined()
  expect((await ui.find({ type: 'Text', text: /^⏸$/ })).props.color).toBe('red')
  expect(await ui.find({ type: 'Text', text: /^widgets\/issue-2$/ })).toBeDefined()
  // 各欄各自上色：result.md 狀態、session 的 TUI 狀態
  expect((await ui.find({ type: 'Text', text: /^idle 12m00s$/ })).props.color).toBe('yellow')
  expect((await ui.find({ type: 'Text', text: /^working 0m05s$/ })).props.color).toBe('green')
  expect((await ui.find({ type: 'Text', text: /session 停在等你輸入/ })).props.color).toBe('red')
  expect(await ui.find({ type: 'Text', text: /^widgets\/issue-1$/ })).toBeDefined()
  await ui.unmount()
})

test('the timer refetches while the pane is open and a failure keeps the last rows', async ($, on) => {
  const clock = mock.clock(on)
  let n = 0
  const calls = stubs(on, () => {
    n += 1
    return n === 1 ? { generated_at: '10:00', errors: [], rows: [row({})] } : 'boom'
  })
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/tmp/widgets' })
  await clock.advance(60_000)
  expect(calls.length).toBe(0) // pane 沒開就不跑
  await $.command.run({ command: 'session-watch', args: '/tmp/widgets' })
  expect(calls.length).toBe(1)
  await clock.advance(60_000)
  expect(calls.length).toBe(2)
  const ui = await $.ui.mount({ ...PANE, surface: 'terminal' })
  expect(await ui.find({ type: 'Text', text: /^讀取失敗：boom/ })).toBeDefined()
  expect(await ui.find({ type: 'Text', text: /^widgets\/issue-1$/ })).toBeDefined()
  await ui.unmount()
})

// 使用者用 Ctrl+X X 關 pane 走的是 ui.close 事件；測試套件發不出那個事件，那條路徑要在真的 TUI 驗
test('/session-watch close stops the timer; auto scopes to this session, all drops the scope', async ($, on) => {
  const clock = mock.clock(on)
  const calls = stubs(on, () => ({ generated_at: '10:00', errors: [], rows: [] }))
  await $.session.start({ surface: 'terminal', isInteractive: true, cwd: '/tmp/widgets' })
  await $.command.run({ command: 'session-watch', args: '/tmp/widgets' })
  expect(calls[0]).toContain('/tmp/widgets')
  await $.command.run({ command: 'session-watch', args: 'close' })
  await clock.advance(120_000)
  expect(calls.length).toBe(1)
  await $.command.run({ command: 'session-watch', args: 'auto' })
  expect(calls.length).toBe(2)
  expect(calls[1]).not.toContain('--repo')
  // session id 每輪重取（/clear 會換 id）；第一輪指定了 repo，沒有取
  expect(calls[1].slice(-4)).toEqual(['--dispatched-by', 'sid-1', '--under', '/tmp/widgets'])
  await $.command.run({ command: 'session-watch', args: '' })
  expect(calls[2].slice(-4)).toEqual(['--dispatched-by', 'sid-2', '--under', '/tmp/widgets'])
  await $.command.run({ command: 'session-watch', args: 'all' })
  expect(calls[3]).not.toContain('--under')
  expect(calls[3]).not.toContain('--dispatched-by')
})
