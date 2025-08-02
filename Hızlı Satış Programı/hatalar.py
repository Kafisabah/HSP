# hatalar.py
# Uygulama genelinde kullanılacak özel hata sınıfları.
# v2: AuthenticationError eklendi.

class DatabaseError(Exception):
    """Veritabanı işlemleri sırasında oluşan genel hatalar için."""
    pass


class DuplicateEntryError(DatabaseError):
    """Veritabanına benzersiz olması gereken bir kayıt eklenmeye çalışıldığında."""
    pass


class SaleIntegrityError(DatabaseError):
    """Satış veya iade işlemleri sırasında veri bütünlüğü sorunları için."""
    pass


class UserInputError(ValueError):
    """Kullanıcı girdisiyle ilgili hatalar için (örn. geçersiz format)."""
    pass

# ***** YENİ HATA SINIFI *****


class AuthenticationError(Exception):
    """Kullanıcı kimlik doğrulama (login, şifre) hataları için."""
    pass
# ***** YENİ HATA SINIFI SONU *****
