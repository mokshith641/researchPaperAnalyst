import pytest
from app.utils.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token
)

def test_password_hashing():
    """Test that passwords are correctly hashed and verified."""
    password = "secret-password"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed) is True
    assert verify_password("wrong-password", hashed) is False

def test_jwt_token_flow():
    """Test access and refresh tokens generation and decoding."""
    subject = "user-id-12345"
    
    # Access token check
    access_token = create_access_token(subject)
    decoded_access = decode_token(access_token, token_type="access")
    assert decoded_access == subject
    
    # Wrong token type checks
    decoded_wrong_type = decode_token(access_token, token_type="refresh")
    assert decoded_wrong_type is None
    
    # Refresh token check
    refresh_token = create_refresh_token(subject)
    decoded_refresh = decode_token(refresh_token, token_type="refresh")
    assert decoded_refresh == subject
    
    # Decode invalid token checks
    assert decode_token("invalid-token-string") is None
