import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import fs from 'node:fs'
import path from 'node:path'
import { fileURLToPath } from 'node:url'

const __dirname = path.dirname(fileURLToPath(import.meta.url))
const VOTER_REQUESTS_FILE = path.resolve(__dirname, 'voter_requests.json')

/**
 * Middleware plugin để Vite dev server xử lý trực tiếp API /api/voter-requests,
 * đồng bộ 2 chiều với file voter_requests.json dùng chung với Admin Python backend.
 */
function voterRequestsApiPlugin() {
  const getRequests = () => {
    try {
      if (!fs.existsSync(VOTER_REQUESTS_FILE)) return []
      const content = fs.readFileSync(VOTER_REQUESTS_FILE, 'utf-8')
      const parsed = JSON.parse(content)
      return Array.isArray(parsed) ? parsed : []
    } catch (_) {
      return []
    }
  }

  const saveRequests = (data) => {
    fs.writeFileSync(VOTER_REQUESTS_FILE, JSON.stringify(data, null, 2), 'utf-8')
  }

  return {
    name: 'voter-requests-api',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url?.split('?')[0]
        if (url !== '/api/voter-requests') {
          return next()
        }

        // GET: Trả về danh sách yêu cầu cử tri
        if (req.method === 'GET') {
          const list = getRequests()
          res.setHeader('Content-Type', 'application/json; charset=utf-8')
          res.statusCode = 200
          res.end(JSON.stringify({ ok: true, requests: list }))
          return
        }

        // POST: Cử tri gửi yêu cầu xác thực mới hoặc cập nhật thông tin
        if (req.method === 'POST') {
          let body = ''
          req.on('data', (chunk) => {
            body += chunk
          })
          req.on('end', () => {
            try {
              const payload = JSON.parse(body || '{}')
              const { name, email, cccd, walletAddress } = payload

              if (!walletAddress || !cccd) {
                res.setHeader('Content-Type', 'application/json; charset=utf-8')
                res.statusCode = 400
                res.end(
                  JSON.stringify({
                    ok: false,
                    error: 'Thiếu thông tin địa chỉ ví hoặc số CCCD/MSSV.',
                  })
                )
                return
              }

              const requests = getRequests()
              const existingIndex = requests.findIndex(
                (r) =>
                  String(r.walletAddress || '').toLowerCase() ===
                  walletAddress.trim().toLowerCase()
              )

              const newRecord = {
                name: (name || 'Cử tri').trim(),
                email: (email || '').trim(),
                cccd: cccd.trim(),
                walletAddress: walletAddress.trim(),
                requestedAt: new Date().toLocaleString('vi-VN'),
                status: 'Chờ duyệt',
              }

              if (existingIndex >= 0) {
                // Nếu ví này đã được Admin xác thực (Whitelist) thì giữ nguyên trạng thái
                if (requests[existingIndex].status === 'Đã xác thực') {
                  res.setHeader('Content-Type', 'application/json; charset=utf-8')
                  res.statusCode = 200
                  res.end(
                    JSON.stringify({
                      ok: true,
                      message: 'Ví của bạn đã được xác thực trước đó trên hệ thống.',
                      request: requests[existingIndex],
                    })
                  )
                  return
                }
                requests[existingIndex] = {
                  ...requests[existingIndex],
                  ...newRecord,
                }
              } else {
                requests.push(newRecord)
              }

              saveRequests(requests)

              res.setHeader('Content-Type', 'application/json; charset=utf-8')
              res.statusCode = 200
              res.end(
                JSON.stringify({
                  ok: true,
                  message: 'Đã gửi yêu cầu xác thực cử tri thành công!',
                  request: newRecord,
                })
              )
            } catch (err) {
              res.setHeader('Content-Type', 'application/json; charset=utf-8')
              res.statusCode = 500
              res.end(
                JSON.stringify({
                  ok: false,
                  error: 'Lỗi máy chủ khi lưu yêu cầu: ' + err.message,
                })
              )
            }
          })
          return
        }

        next()
      })
    },
  }
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    react(),
    tailwindcss(),
    voterRequestsApiPlugin(),
  ],
  // Cho phép Vite đọc trực tiếp CONTRACT_ADDRESS và RPC_URL từ chung file .env với Python
  envPrefix: ['VITE_', 'CONTRACT_', 'RPC_'],
})
