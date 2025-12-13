import os
import shutil
import sys
import tempfile
from collections.abc import Generator
from datetime import datetime, timezone
from pathlib import Path
from textwrap import dedent
from uuid import uuid4

import pytest
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text, Uuid
from sqlalchemy.orm import declarative_base, mapped_column

UTC = timezone.utc


@pytest.fixture
def metaclass():
    Base = declarative_base()

    class User(Base):
        __tablename__ = "users"

        id = mapped_column(Uuid, primary_key=True, default=uuid4())
        display_name = mapped_column(String(100))
        created = mapped_column(DateTime, nullable=False, default=datetime.now(UTC))

    class Post(Base):
        __tablename__ = "posts"

        id = mapped_column(Uuid, primary_key=True, default=uuid4())
        created = mapped_column(DateTime, nullable=False, default=datetime.now(UTC))
        author = mapped_column(ForeignKey(User.id), nullable=False)
        live = mapped_column(Boolean, default=False, comment="True if post is published")
        content = mapped_column(Text, default="")

    class Comment(Base):
        __tablename__ = "comments"

        id = mapped_column(Uuid, primary_key=True, default=uuid4())
        created = mapped_column(DateTime, nullable=False, default=datetime.now(UTC))
        post = mapped_column(Uuid, ForeignKey(Post.id), default=uuid4())
        author = mapped_column(ForeignKey(User.id), nullable=False)
        live = mapped_column(Boolean, default=False)
        content = mapped_column(Text, default="")

    return Base.metadata


@pytest.fixture
def package_path() -> Generator[Path, None, None]:
    template_path = Path(os.path.dirname(os.path.realpath(__file__))) / "assets"
    with tempfile.TemporaryDirectory() as package_path:
        shutil.copytree(template_path, package_path, dirs_exist_ok=True)
        os.chdir(package_path)
        # RATIONALE: Purge cached 'example' modules so the new temp directory path is used for imports.
        # Without this, earlier tests leave sys.modules['example'] with a __path__ pointing at a deleted
        # temp directory. Later tests then fail to import submodules (e.g. example.cardinalities) because
        # Python reuses the stale package object and doesn't refresh its search path. Removing only these
        # entries enforces a clean import and prevents cross-test leakage / flakiness.
        for name in list(sys.modules.keys()):
            if name == "example" or name.startswith("example."):
                del sys.modules[name]
        yield Path(package_path)


@pytest.fixture()
def mermaid_full_string_preseve_column_sort() -> str:
    return """erDiagram
  users {
    CHAR(32) id PK
    VARCHAR(100) display_name "nullable"
    DATETIME created
  }

  posts {
    CHAR(32) id PK
    DATETIME created
    CHAR(32) author FK
    BOOLEAN live "True if post is published,nullable"
    TEXT content "nullable"
  }

  comments {
    CHAR(32) id PK
    DATETIME created
    CHAR(32) post FK "nullable"
    CHAR(32) author FK
    BOOLEAN live "nullable"
    TEXT content "nullable"
  }

  users ||--o{ posts : author
  posts ||--o{ comments : post
  users ||--o{ comments : author
"""


@pytest.fixture()
def dot_full_string_preseve_column_sort() -> str:
    return """graph database {
users [label=<
    <table border="0" cellborder="1" cellspacing="0" cellpadding="4">
        <tr><td colspan="3" bgcolor="lightblue"><b>users</b></td></tr>
        <tr><td align="left">CHAR(32)</td><td align="left">id</td><td>Primary Key</td></tr>
        <tr><td align="left">VARCHAR(100)</td><td align="left">display_name</td><td></td></tr>
        <tr><td align="left">DATETIME</td><td align="left">created</td><td></td></tr>
    </table>
>, shape=none, margin=0];
posts [label=<
    <table border="0" cellborder="1" cellspacing="0" cellpadding="4">
        <tr><td colspan="3" bgcolor="lightblue"><b>posts</b></td></tr>
        <tr><td align="left">CHAR(32)</td><td align="left">id</td><td>Primary Key</td></tr>
        <tr><td align="left">DATETIME</td><td align="left">created</td><td></td></tr>
        <tr><td align="left">CHAR(32)</td><td align="left">author</td><td>Foreign Key</td></tr>
        <tr><td align="left">BOOLEAN</td><td align="left">live</td><td></td></tr>
        <tr><td align="left">TEXT</td><td align="left">content</td><td></td></tr>
    </table>
>, shape=none, margin=0];
users -- posts [label=author, dir=both, arrowhead=crow, arrowtail=none];
comments [label=<
    <table border="0" cellborder="1" cellspacing="0" cellpadding="4">
        <tr><td colspan="3" bgcolor="lightblue"><b>comments</b></td></tr>
        <tr><td align="left">CHAR(32)</td><td align="left">id</td><td>Primary Key</td></tr>
        <tr><td align="left">DATETIME</td><td align="left">created</td><td></td></tr>
        <tr><td align="left">CHAR(32)</td><td align="left">post</td><td>Foreign Key</td></tr>
        <tr><td align="left">CHAR(32)</td><td align="left">author</td><td>Foreign Key</td></tr>
        <tr><td align="left">BOOLEAN</td><td align="left">live</td><td></td></tr>
        <tr><td align="left">TEXT</td><td align="left">content</td><td></td></tr>
    </table>
>, shape=none, margin=0];
posts -- comments [label=post, dir=both, arrowhead=crow, arrowtail=none];
users -- comments [label=author, dir=both, arrowhead=crow, arrowtail=none];
}
"""


@pytest.fixture(name="expected_mermaid_smaller_graph")
def fixture_expected_mermaid_smaller_graph() -> str:
    return dedent("""\
        # Test Directory
    
        Please ignore.
        
        ## Schema
        
        <!-- BEGIN_SQLALCHEMY_DOCS -->
        ```mermaid
        
        ---
            config:
                layout: dagre
        ---
        erDiagram
          users {
            CHAR(32) id PK
            DATETIME created
            VARCHAR(100) display_name "nullable"
          }
        
          posts {
            CHAR(32) id PK
            CHAR(32) author FK
            TEXT content "nullable"
            DATETIME created
            BOOLEAN live "True if post is published,nullable"
          }
        
          users ||--o{ posts : author
        
        ```
        <!-- END_SQLALCHEMY_DOCS -->
    """)


@pytest.fixture(name="expected_mermaid_complete_graph")
def fixture_expected_mermaid_complete_graph() -> str:
    return dedent("""\
        # Test Directory
    
        Please ignore.
        
        ## Schema
        
        <!-- BEGIN_SQLALCHEMY_DOCS -->
        ```mermaid
        
        ---
            config:
                layout: dagre
        ---
        erDiagram
          users {
            CHAR(32) id PK
            DATETIME created
            VARCHAR(100) display_name "nullable"
          }
        
          posts {
            CHAR(32) id PK
            CHAR(32) author FK
            TEXT content "nullable"
            DATETIME created
            BOOLEAN live "True if post is published,nullable"
          }
        
          comments {
            CHAR(32) id PK
            CHAR(32) author FK
            CHAR(32) post FK "nullable"
            TEXT content "nullable"
            DATETIME created
            BOOLEAN live "nullable"
          }
        
          users ||--o{ posts : author
          posts ||--o{ comments : post
          users ||--o{ comments : author
        
        ```
        <!-- END_SQLALCHEMY_DOCS -->
    """)


@pytest.fixture(name="expected_mermaid_cardinalities_graph")
def fixture_expected_mermaid_cardinalities_graph() -> str:
    return dedent("""\
        # Test Directory
    
        Please ignore.
        
        ## Schema
        
        <!-- BEGIN_SQLALCHEMY_DOCS -->
        ```mermaid
        erDiagram
          bar {
            CHAR(32) id PK
          }

          baz {
            CHAR(32) id PK
          }

          beep {
            CHAR(32) id PK
          }

          foo {
            CHAR(32) id PK
            CHAR(32) bar_id FK
            CHAR(32) baz_id FK
            CHAR(32) beep_id FK
            VARCHAR boop
          }

          bar ||--o| foo : bar_id
          baz ||--o| foo : baz_id
          beep ||--o{ foo : beep_id

        ```
        <!-- END_SQLALCHEMY_DOCS -->
    """)


@pytest.fixture
def single_level_package_path() -> Generator[Path, None, None]:
    """Create a package structure with single-level subpackages for testing pattern example.*.models.
    
    Structure:
    example/
        base.py
        foo/
            models.py
        bar/
            models.py
    """
    with tempfile.TemporaryDirectory() as package_path:
        package_dir = Path(package_path)
        example_dir = package_dir / "example"
        example_dir.mkdir(parents=True, exist_ok=True)
        
        # Create base
        (example_dir / "base.py").write_text(
            dedent("""\
                from sqlalchemy.orm import declarative_base

                Base = declarative_base()
            """)
        )
        (example_dir / "__init__.py").write_text("")
        
        # Create example.foo.models
        (example_dir / "foo").mkdir(parents=True, exist_ok=True)
        (example_dir / "foo" / "__init__.py").write_text("")
        (example_dir / "foo" / "models.py").write_text(
            dedent("""\
                from sqlalchemy import String
                from sqlalchemy.orm import mapped_column
                from ..base import Base

                class FooModel(Base):
                    __tablename__ = 'foo_table'
                    id = mapped_column(String, primary_key=True)
            """)
        )
        
        # Create example.bar.models
        (example_dir / "bar").mkdir(parents=True, exist_ok=True)
        (example_dir / "bar" / "__init__.py").write_text("")
        (example_dir / "bar" / "models.py").write_text(
            dedent("""\
                from sqlalchemy import String
                from sqlalchemy.orm import mapped_column
                from ..base import Base

                class BarModel(Base):
                    __tablename__ = 'bar_table'
                    id = mapped_column(String, primary_key=True)
            """)
        )
        
        os.chdir(package_path)

        # Cleanup
        for name in list(sys.modules.keys()):
            if name == "example" or name.startswith("example."):
                del sys.modules[name]
        
        yield Path(package_path)


@pytest.fixture
def nested_package_path() -> Generator[Path, None, None]:
    """Create a package structure with nested subpackages for testing multi-level glob patterns.

    Structure:
    example/
        domain/
            users/
                models.py
            products/
                models.py
        api/
            v1/
                models.py
    """
    with tempfile.TemporaryDirectory() as package_path:
        package_dir = Path(package_path)
        example_dir = package_dir / "example"
        example_dir.mkdir(parents=True, exist_ok=True)
        
        # Create base
        (example_dir / "base.py").write_text(
            dedent("""\
                from sqlalchemy.orm import declarative_base

                Base = declarative_base()
            """)
        )
        (example_dir / "__init__.py").write_text("")
        
        # Create domain.users.models
        (example_dir / "domain" / "users").mkdir(parents=True, exist_ok=True)
        (example_dir / "domain" / "users" / "__init__.py").write_text("")
        (example_dir / "domain" / "users" / "models.py").write_text(
            dedent("""\
                from sqlalchemy import String
                from sqlalchemy.orm import mapped_column
                from ...base import Base

                class User(Base):
                    __tablename__ = 'users'
                    id = mapped_column(String, primary_key=True)
            """)
        )
        
        # Create domain.products.models
        (example_dir / "domain" / "products").mkdir(parents=True, exist_ok=True)
        (example_dir / "domain" / "products" / "__init__.py").write_text("")
        (example_dir / "domain" / "products" / "models.py").write_text(
            dedent("""\
                from sqlalchemy import String
                from sqlalchemy.orm import mapped_column
                from ...base import Base

                class Product(Base):
                    __tablename__ = 'products'
                    id = mapped_column(String, primary_key=True)
            """)
        )
        
        # Create api.v1.models
        (example_dir / "api" / "v1").mkdir(parents=True, exist_ok=True)
        (example_dir / "api" / "v1" / "__init__.py").write_text("")
        (example_dir / "api" / "v1" / "models.py").write_text(
            dedent("""\
                from sqlalchemy import String
                from sqlalchemy.orm import mapped_column
                from ...base import Base

                class APIResource(Base):
                    __tablename__ = 'api_resources'
                    id = mapped_column(String, primary_key=True)
            """)
        )
        
        os.chdir(package_path)

        # Cleanup
        for name in list(sys.modules.keys()):
            if name == "example" or name.startswith("example."):
                del sys.modules[name]
        
        yield Path(package_path)


@pytest.fixture
def multi_star_package_path() -> Generator[Path, None, None]:
    """Create a package structure for testing patterns with multiple stars.

    Structure:
    example/
        v1/
            api/
                users/
                    models.py
        v2/
            api/
                products/
                    models.py
    """
    with tempfile.TemporaryDirectory() as package_path:
        package_dir = Path(package_path)
        example_dir = package_dir / "example"
        example_dir.mkdir(parents=True, exist_ok=True)
        
        # Create base
        (example_dir / "base.py").write_text(
            dedent("""\
                from sqlalchemy.orm import declarative_base

                Base = declarative_base()
            """)
        )
        (example_dir / "__init__.py").write_text("")
        
        # Create v1.api.users.models
        (example_dir / "v1" / "api" / "users").mkdir(parents=True, exist_ok=True)
        (example_dir / "v1" / "api" / "users" / "__init__.py").write_text("")
        (example_dir / "v1" / "api" / "users" / "models.py").write_text(
            dedent("""\
                from sqlalchemy import String
                from sqlalchemy.orm import mapped_column
                from ....base import Base

                class V1User(Base):
                    __tablename__ = 'v1_users'
                    id = mapped_column(String, primary_key=True)
            """)
        )
        
        # Create v2.api.products.models
        (example_dir / "v2" / "api" / "products").mkdir(parents=True, exist_ok=True)
        (example_dir / "v2" / "api" / "products" / "__init__.py").write_text("")
        (example_dir / "v2" / "api" / "products" / "models.py").write_text(
            dedent("""\
                from sqlalchemy import String
                from sqlalchemy.orm import mapped_column
                from ....base import Base

                class V2Product(Base):
                    __tablename__ = 'v2_products'
                    id = mapped_column(String, primary_key=True)
            """)
        )
        
        os.chdir(package_path)

        # Cleanup
        for name in list(sys.modules.keys()):
            if name == "example" or name.startswith("example."):
                del sys.modules[name]
        
        yield Path(package_path)


@pytest.fixture
def namespace_package_path() -> Generator[Path, None, None]:
    """Create a namespace package structure (PEP 420) for testing.

    Structure (two separate directories that form one namespace):
    project1/
        example/  (NO __init__.py)
            subpackage_a/
                models.py
    project2/
        example/  (NO __init__.py)
            subpackage_b/
                models.py

    Both are added to sys.path separately.
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)
        
        # Project 1
        project1 = temp_path / "project1"
        (project1 / "example").mkdir(parents=True, exist_ok=True)
        (project1 / "example" / "subpackage_a").mkdir(parents=True, exist_ok=True)
        (project1 / "example" / "subpackage_a" / "__init__.py").write_text("")
        (project1 / "example" / "base.py").write_text(
            dedent("""\
                from sqlalchemy.orm import declarative_base

                Base = declarative_base()
            """)
        )
        (project1 / "example" / "subpackage_a" / "models.py").write_text(
            dedent("""\
                from sqlalchemy import String
                from sqlalchemy.orm import mapped_column
                from ..base import Base

                class SubpackageAModel(Base):
                    __tablename__ = 'subpackage_a_table'
                    id = mapped_column(String, primary_key=True)
            """)
        )
        
        # Project 2
        project2 = temp_path / "project2"
        (project2 / "example").mkdir(parents=True, exist_ok=True)
        (project2 / "example" / "subpackage_b").mkdir(parents=True, exist_ok=True)
        (project2 / "example" / "subpackage_b" / "__init__.py").write_text("")
        (project2 / "example" / "subpackage_b" / "models.py").write_text(
            dedent("""\
                from sqlalchemy import String
                from sqlalchemy.orm import mapped_column
                from ..base import Base

                class SubpackageBModel(Base):
                    __tablename__ = 'subpackage_b_table'
                    id = mapped_column(String, primary_key=True)
            """)
        )
        
        # We need to add both to sys.path
        sys.path.insert(0, str(project1))
        sys.path.insert(0, str(project2))
        
        os.chdir(str(temp_path))
        
        # Cleanup
        for name in list(sys.modules.keys()):
            if name == "example" or name.startswith("example."):
                del sys.modules[name]
        
        try:
            yield temp_path
        finally:
            # Remove from sys.path
            if str(project1) in sys.path:
                sys.path.remove(str(project1))
            if str(project2) in sys.path:
                sys.path.remove(str(project2))