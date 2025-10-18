# OpenAlgo Auto-Startup Feature

## Overview

The Auto-Startup feature automatically logs in users and authenticates with brokers when the OpenAlgo server starts, eliminating the need for manual login and making the system ready to accept API orders immediately.

## Features

- ✅ **Automatic User Login**: Logs in with configured credentials on server startup
- ✅ **Automatic Broker Authentication**: Authenticates with IIFL broker automatically
- ✅ **System Readiness Verification**: Ensures the system is ready for API orders
- ✅ **Retry Logic**: Automatically retries failed authentication attempts
- ✅ **Background Processing**: Runs in a separate thread to avoid blocking server startup
- ✅ **Configurable Delay**: Waits for server to fully initialize before attempting login

## Quick Setup

### 1. Configure Auto-Startup

Run the configuration script:

```bash
python configure_auto_startup.py
```

Or manually edit your `.env` file:

```bash
# Auto-Startup Configuration
AUTO_STARTUP_USERNAME = 'your_username'
AUTO_STARTUP_PASSWORD = 'your_password'
AUTO_STARTUP_DELAY = '10'  # Delay in seconds before attempting auto-login
```

### 2. Ensure Broker Credentials

Make sure your broker credentials are configured:

```bash
BROKER_API_KEY = 'your_iifl_api_key'
BROKER_API_SECRET = 'your_iifl_api_secret'
BROKER_API_KEY_MARKET = 'your_iifl_market_api_key'
BROKER_API_SECRET_MARKET = 'your_iifl_market_api_secret'
```

### 3. Restart OpenAlgo

Restart your OpenAlgo server to activate auto-startup:

```bash
python app.py
```

## How It Works

### Startup Process

1. **Server Initialization**: OpenAlgo server starts normally
2. **Auto-Startup Check**: System checks if auto-startup is enabled
3. **Background Thread**: Auto-startup process runs in a separate thread
4. **Delay Period**: Waits for server to fully initialize (default: 10 seconds)
5. **User Login**: Automatically logs in with configured credentials
6. **Broker Authentication**: Authenticates with IIFL broker
7. **System Verification**: Verifies system is ready for API orders

### Retry Logic

- **Max Retries**: 3 attempts for each step
- **Retry Delay**: 5 seconds between attempts
- **Graceful Failure**: Logs errors but doesn't crash the server

## Configuration Options

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `AUTO_STARTUP_USERNAME` | OpenAlgo username | - | Yes |
| `AUTO_STARTUP_PASSWORD` | OpenAlgo password | - | Yes |
| `AUTO_STARTUP_DELAY` | Delay before auto-login (seconds) | 10 | No |

### Broker Credentials

| Variable | Description | Required |
|----------|-------------|----------|
| `BROKER_API_KEY` | IIFL API Key | Yes |
| `BROKER_API_SECRET` | IIFL API Secret | Yes |
| `BROKER_API_KEY_MARKET` | IIFL Market API Key | Yes |
| `BROKER_API_SECRET_MARKET` | IIFL Market API Secret | Yes |

## Testing

### Test Auto-Startup

Run the test script to verify functionality:

```bash
python test_auto_startup.py
```

### Manual Testing

1. **Check Logs**: Look for auto-startup messages in `log/openalgo.log`
2. **Access Dashboard**: Visit `http://localhost:5000/dashboard` - should work without manual login
3. **API Endpoints**: Test API endpoints - should be ready for orders

### Expected Log Messages

```
[INFO] Auto-startup: Enabled - will attempt automatic login after server startup
[INFO] Auto-startup: Waiting 10 seconds for server to initialize...
[INFO] Auto-startup: Logging in user your_username
[INFO] Auto-startup: User login successful
[INFO] Auto-startup: Authenticating with broker
[INFO] Auto-startup: Broker authentication successful!
[INFO] Auto-startup: System ready for API orders
[INFO] 🎉 Auto-startup completed successfully!
```

## Troubleshooting

### Common Issues

#### 1. Auto-Startup Not Working

**Symptoms**: Manual login still required

**Solutions**:
- Check if environment variables are set correctly
- Verify broker credentials are valid
- Check server logs for error messages
- Ensure server has been restarted after configuration

#### 2. Broker Authentication Fails

**Symptoms**: User logs in but broker authentication fails

**Solutions**:
- Verify IIFL API credentials are correct
- Check if IIFL API account is active
- Test credentials manually using `complete_flow_simulation.py`
- Check network connectivity to IIFL servers

#### 3. System Not Ready

**Symptoms**: Login works but API endpoints return errors

**Solutions**:
- Check master contract download status
- Verify broker tokens are stored in database
- Check if session is properly maintained

### Debug Commands

```bash
# Check environment variables
python -c "import os; print('AUTO_STARTUP_USERNAME:', os.getenv('AUTO_STARTUP_USERNAME'))"

# Test auto-startup functionality
python test_auto_startup.py

# Check server logs
tail -f log/openalgo.log | grep "Auto-startup"

# Test manual login flow
python complete_flow_simulation.py
```

## Security Considerations

### Credential Storage

- **Environment Variables**: Credentials are stored in `.env` file
- **File Permissions**: Ensure `.env` file has restricted permissions
- **Version Control**: Never commit `.env` file to version control

### Session Management

- **Session Expiry**: Sessions expire at 3:00 AM IST daily
- **Token Encryption**: Broker tokens are encrypted in database
- **CSRF Protection**: Auto-startup respects CSRF protection

## Advanced Configuration

### Custom Delay

For slower systems, increase the delay:

```bash
AUTO_STARTUP_DELAY = '30'  # Wait 30 seconds
```

### Disable Auto-Startup

Comment out or remove auto-startup variables:

```bash
# AUTO_STARTUP_USERNAME = 'your_username'
# AUTO_STARTUP_PASSWORD = 'your_password'
```

### Multiple Users

Auto-startup supports only one user. For multiple users, use manual login or API key authentication.

## Integration with Existing Systems

### Docker

Auto-startup works with Docker containers. Set environment variables in your Docker configuration:

```dockerfile
ENV AUTO_STARTUP_USERNAME=your_username
ENV AUTO_STARTUP_PASSWORD=your_password
```

### Production Deployment

For production environments:

1. Use strong, unique passwords
2. Regularly rotate credentials
3. Monitor auto-startup logs
4. Set up alerts for authentication failures

## Support

### Getting Help

1. **Check Logs**: Always check `log/openalgo.log` first
2. **Test Scripts**: Use provided test scripts for debugging
3. **Configuration**: Verify all environment variables are set correctly
4. **Documentation**: Refer to this documentation for troubleshooting

### Reporting Issues

When reporting issues, include:

- OpenAlgo version
- Operating system
- Auto-startup configuration (without credentials)
- Relevant log entries
- Steps to reproduce the issue

---

**Note**: Auto-startup is designed for convenience and should not replace proper security practices. Always use strong credentials and monitor your system for any unauthorized access.
