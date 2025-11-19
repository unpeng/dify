# Dify 后台管理 iframe 集成指南

本指南介绍如何将 Dify 后台管理系统以 iframe 方式集成到外部系统中，并实现免登录功能。

## 功能特性

- **iframe 嵌入支持**：支持将 Dify 后台管理系统嵌入到外部系统页面中
- **免登录集成**：通过外部系统的 token 实现自动登录
- **跨域支持**：配置了适当的 CORS 和 iframe 响应头
- **用户自动创建**：支持根据外部系统用户信息自动创建 Dify 用户
- **工作空间管理**：自动为新用户创建工作空间

## 配置说明

### 1. 环境变量配置

在 `.env` 文件中添加以下配置：

```bash
# 启用 iframe 嵌入
ALLOW_EMBED=true

# 允许嵌入的域名（逗号分隔，* 表示允许所有域名）
IFRAME_ALLOWED_ORIGINS=*

# iframe 认证 token 有效期（分钟）
IFRAME_AUTH_TOKEN_EXPIRE_MINUTES=60

# 外部系统 token 验证 URL（可选）
EXTERNAL_TOKEN_VERIFY_URL=https://your-system.com/api/verify-token

# 外部系统用户信息获取 URL（可选）
EXTERNAL_USER_INFO_URL=https://your-system.com/api/user-info

# 外部系统 API 密钥（可选）
EXTERNAL_SYSTEM_API_KEY=your-api-key

# 是否启用 iframe 通信日志
IFRAME_COMMUNICATION_LOG_ENABLED=false

# iframe 会话超时时间（分钟）
IFRAME_SESSION_TIMEOUT_MINUTES=480

# 是否自动创建不存在的用户
IFRAME_AUTO_CREATE_USER=true

# 默认用户角色
IFRAME_DEFAULT_USER_ROLE=owner

# 默认界面语言
IFRAME_DEFAULT_LANGUAGE=zh-Hans
```

### 2. 外部系统集成

#### 2.1 认证流程

1. 外部系统获取用户的认证 token
2. 调用 Dify 的 iframe 认证接口
3. Dify 验证 token 并创建用户会话
4. 加载 iframe 并自动登录

#### 2.2 API 接口

**iframe 认证接口**

```http
POST /console/api/iframe-auth
Content-Type: application/json

{
  "token": "your-external-token",
  "tenant": "tenant-code"
}
```

**响应**

```json
{
  "result": "success",
  "user": {
    "id": "user-id",
    "name": "User Name",
    "email": "user@example.com",
    "role": "admin"  /* owner / admin / editor / normal */
  }
}
```


**iframe 配置接口**

```http
GET /console/api/iframe-config
```

**iframe 健康检查接口**

```http
GET /console/api/iframe-health
```

### 3. 前端集成示例

```html
<!DOCTYPE html>
<html>
<head>
    <title>Dify 集成示例</title>
</head>
<body>
    <div id="dify-container">
        <iframe id="dify-iframe" style="width: 100%; height: 800px; border: none;"></iframe>
    </div>

    <script>
        async function loadDify() {
            const userToken = 'your-user-token';
            const userEmail = 'user@example.com';
            
            try {
                // 1. 认证用户
                const authResponse = await fetch('/console/api/iframe-auth', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    credentials: 'include',
                    body: JSON.stringify({
                        token: userToken,
                        email: userEmail
                    })
                });
                
                if (authResponse.ok) {
                    // 2. 加载 iframe
                    const iframe = document.getElementById('dify-iframe');
                    iframe.src = 'http://localhost:3000';
                    
                    // 3. 设置消息监听
                    window.addEventListener('message', function(event) {
                        if (event.origin !== 'http://localhost:3000') return;
                        
                        console.log('收到 Dify 消息:', event.data);
                    });
                } else {
                    console.error('认证失败');
                }
            } catch (error) {
                console.error('加载失败:', error);
            }
        }
        
        // 页面加载时执行
        loadDify();
    </script>
</body>
</html>
```

## 自定义实现

### 1. Token 验证

如果需要自定义 token 验证逻辑，可以修改 `controllers/console/auth/iframe_auth.py` 中的 `_verify_iframe_token` 方法：

```python
def _verify_iframe_token(self, token: str, email: str = None) -> bool:
    """自定义 token 验证逻辑"""
    try:
        # 实现您的 token 验证逻辑
        # 例如：JWT 验证、调用外部 API 等
        
        # JWT 示例
        import jwt
        payload = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
        return payload.get('email') == email
        
    except Exception:
        return False
```

### 2. 用户信息获取

修改 `_get_user_from_token` 方法来自定义用户信息获取逻辑：

```python
def _get_user_from_token(self, token: str) -> dict:
    """自定义用户信息获取逻辑"""
    try:
        # 从 JWT 中解析用户信息
        import jwt
        payload = jwt.decode(token, 'your-secret-key', algorithms=['HS256'])
        
        return {
            "email": payload.get('email'),
            "name": payload.get('name'),
            "external_id": payload.get('user_id')
        }
    except Exception:
        return None
```

## 安全考虑

1. **Token 验证**：确保实现安全的 token 验证机制
2. **域名限制**：在生产环境中限制允许嵌入的域名
3. **HTTPS**：在生产环境中使用 HTTPS
4. **会话管理**：合理设置会话超时时间
5. **权限控制**：根据外部系统的用户权限设置 Dify 用户权限

## 故障排除

### 1. iframe 无法加载

- 检查 `ALLOW_EMBED` 是否设置为 `true`
- 检查浏览器控制台是否有 X-Frame-Options 错误
- 确认域名是否在允许列表中

### 2. 认证失败

- 检查 token 格式是否正确
- 确认外部 API 配置是否正确
- 查看服务器日志获取详细错误信息

### 3. 跨域问题

- 确认 CORS 配置是否正确
- 检查 cookie 的 SameSite 设置
- 确保使用 HTTPS（如果需要）

## 示例文件

项目中包含了一个完整的集成示例：`templates/iframe_integration_example.html`

您可以参考这个示例来实现自己的集成方案。

## 技术支持

如果在集成过程中遇到问题，请：

1. 检查服务器日志
2. 确认配置是否正确
3. 参考示例代码
4. 联系技术支持团队
