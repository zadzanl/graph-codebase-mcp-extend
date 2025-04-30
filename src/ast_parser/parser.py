import ast
import os
from typing import Dict, List, Optional, Tuple, Any, Union, Set
import json


class CodeNode:
    """代表程式碼中的節點（類別、函數、變數等）"""

    def __init__(
        self,
        node_id: str,
        node_type: str,
        name: str,
        file_path: str,
        line_no: int,
        end_line_no: Optional[int] = None,
        properties: Dict[str, Any] = None,
    ):
        self.node_id = node_id
        self.node_type = node_type
        self.name = name
        self.file_path = file_path
        self.line_no = line_no
        self.end_line_no = end_line_no
        self.properties = properties or {}
        self.code_snippet = ""

    def __str__(self):
        return f"{self.node_type}:{self.name} ({self.file_path}:{self.line_no})"


class CodeRelation:
    """代表程式碼中的關係（調用、繼承等）"""

    def __init__(
        self,
        source_id: str,
        target_id: str,
        relation_type: str,
        properties: Dict[str, Any] = None,
    ):
        self.source_id = source_id
        self.target_id = target_id
        self.relation_type = relation_type
        self.properties = properties or {}

    def __str__(self):
        return f"{self.source_id} -{self.relation_type}-> {self.target_id}"


class ASTParser:
    """使用 Python AST 模組解析程式碼的解析器"""

    def __init__(self):
        self.nodes: Dict[str, CodeNode] = {}
        self.relations: List[CodeRelation] = []
        self.current_file: str = ""
        self.current_function: Optional[str] = None
        self.current_class: Optional[str] = None
        self.imports: Dict[str, str] = {}
        # 用於追蹤模組中的定義
        self.module_definitions: Dict[str, Dict[str, str]] = {}
        # 用於追蹤待處理的導入依賴關係
        self.pending_imports: List[Dict[str, Any]] = []
        # 用於追蹤模組名稱與檔案節點的對應關係
        self.module_to_file: Dict[str, str] = {}
        # 用於追蹤已建立的關係，避免重複
        self.established_relations: Set[str] = set()

    def parse_directory(self, directory_path: str) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """解析目錄中的所有Python檔案"""
        self.nodes = {}
        self.relations = []
        self.module_definitions = {}
        self.pending_imports = []
        self.module_to_file = {}
        self.established_relations = set()

        # 第一遍：創建所有節點並建立模組定義索引
        for root, _, files in os.walk(directory_path):
            for file_name in files:
                if file_name.endswith(".py"):
                    file_path = os.path.join(root, file_name)
                    self.parse_file(file_path, build_index=True)

        # 第二遍：處理所有待處理的導入關係
        self._process_pending_imports()

        return self.nodes, self.relations
        
    def parse_file(self, file_path: str, build_index: bool = False) -> Tuple[Dict[str, CodeNode], List[CodeRelation]]:
        """解析單個Python檔案"""
        print(f"解析檔案: {file_path}")
        self.current_file = file_path
        self.imports = {}

        try:
            with open(file_path, "r", encoding="utf-8") as file:
                file_content = file.read()
                tree = ast.parse(file_content)
                file_node_id = self._create_file_node(file_path)
                
                # 生成模組名稱，用於索引
                module_name = os.path.splitext(os.path.basename(file_path))[0]
                if build_index:
                    if module_name not in self.module_definitions:
                        self.module_definitions[module_name] = {}
                    # 關聯模組名稱與檔案節點
                    self.module_to_file[module_name] = file_node_id
                
                self._parse_ast(tree, build_index, module_name)

            return self.nodes, self.relations
        except Exception as e:
            print(f"解析檔案 {file_path} 時發生錯誤: {e}")
            return {}, []

    def _create_file_node(self, file_path: str) -> str:
        """創建檔案節點"""
        file_name = os.path.basename(file_path)
        node_id = f"file:{file_path}"
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="File",
            name=file_name,
            file_path=file_path,
            line_no=0,
        )
        return node_id

    def _get_node_id(self, node_type: str, name: str, file_path: str, line_no: int) -> str:
        """生成節點唯一標識符"""
        return f"{node_type}:{file_path}:{name}:{line_no}"

    def _parse_ast(self, tree: ast.AST, build_index: bool = False, module_name: str = "") -> None:
        """遞迴解析AST樹狀結構"""
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.ClassDef):
                node_id = self._parse_class(node)
                if build_index and module_name:
                    self.module_definitions[module_name][node.name] = node_id
            elif isinstance(node, ast.FunctionDef):
                node_id = self._parse_function(node)
                if build_index and module_name:
                    self.module_definitions[module_name][node.name] = node_id
            elif isinstance(node, ast.Import) or isinstance(node, ast.ImportFrom):
                self._parse_import(node)
            elif isinstance(node, ast.Assign):
                self._parse_assignment(node)
            else:
                self._parse_ast(node, build_index, module_name)

    def _parse_class(self, node: ast.ClassDef) -> str:
        """解析類別定義"""
        prev_class = self.current_class
        node_id = self._get_node_id("Class", node.name, self.current_file, node.lineno)
        
        # 創建類別節點
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="Class",
            name=node.name,
            file_path=self.current_file,
            line_no=node.lineno,
            end_line_no=getattr(node, "end_lineno", None),
        )
        
        # 創建檔案包含類別的關係
        file_node_id = f"file:{self.current_file}"
        self.relations.append(
            CodeRelation(
                source_id=file_node_id,
                target_id=node_id,
                relation_type="CONTAINS",
            )
        )
        
        # 處理類別繼承
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                if base_name in self.imports:
                    # 將此繼承關係添加到待處理隊列
                    self.pending_imports.append({
                        "type": "EXTENDS",
                        "source_id": node_id,
                        "imported_module": self.imports[base_name].split(".")[0],
                        "imported_name": self.imports[base_name].split(".")[-1] 
                            if "." in self.imports[base_name] else self.imports[base_name],
                        "original_name": base_name
                    })
                else:
                    # 創建繼承關係
                    self.relations.append(
                        CodeRelation(
                            source_id=node_id,
                            target_id=f"Class:{self.current_file}:{base_name}:0",
                            relation_type="EXTENDS",
                        )
                    )
        
        # 設置當前類別上下文
        self.current_class = node_id
        
        # 解析類別內部成員
        for item in node.body:
            if isinstance(item, ast.FunctionDef):
                self._parse_method(item)
            elif isinstance(item, ast.Assign):
                self._parse_class_attribute(item)
        
        # 恢復上下文
        self.current_class = prev_class
        
        return node_id

    def _parse_method(self, node: ast.FunctionDef) -> None:
        """解析類別方法"""
        node_id = self._get_node_id("Method", node.name, self.current_file, node.lineno)
        
        # 創建方法節點
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="Method",
            name=node.name,
            file_path=self.current_file,
            line_no=node.lineno,
            end_line_no=getattr(node, "end_lineno", None),
            properties={"is_method": True},
        )
        
        # 創建類別定義方法的關係
        self.relations.append(
            CodeRelation(
                source_id=self.current_class,
                target_id=node_id,
                relation_type="DEFINES",
            )
        )
        
        # 設置當前函數上下文並解析函數體
        prev_function = self.current_function
        self.current_function = node_id
        
        # 解析函數參數
        self._parse_function_args(node, node_id)
        
        # 解析函數體
        for item in node.body:
            if isinstance(item, ast.Expr):
                if isinstance(item.value, ast.Str):
                    # 處理函數文檔字串
                    self.nodes[node_id].properties["docstring"] = item.value.s
            
            # 尋找函數調用
            self._find_function_calls(item)
        
        # 恢復上下文
        self.current_function = prev_function

    def _parse_function(self, node: ast.FunctionDef) -> str:
        """解析函數定義"""
        node_id = self._get_node_id("Function", node.name, self.current_file, node.lineno)
        
        # 創建函數節點
        self.nodes[node_id] = CodeNode(
            node_id=node_id,
            node_type="Function",
            name=node.name,
            file_path=self.current_file,
            line_no=node.lineno,
            end_line_no=getattr(node, "end_lineno", None),
            properties={"is_method": False},
        )
        
        # 創建檔案包含函數的關係
        file_node_id = f"file:{self.current_file}"
        self.relations.append(
            CodeRelation(
                source_id=file_node_id,
                target_id=node_id,
                relation_type="CONTAINS",
            )
        )
        
        # 設置當前函數上下文
        prev_function = self.current_function
        self.current_function = node_id
        
        # 解析函數參數
        self._parse_function_args(node, node_id)
        
        # 解析函數體
        for item in node.body:
            if isinstance(item, ast.Expr):
                if isinstance(item.value, ast.Str):
                    # 處理函數文檔字串
                    self.nodes[node_id].properties["docstring"] = item.value.s
            
            # 尋找函數調用
            self._find_function_calls(item)
        
        # 恢復上下文
        self.current_function = prev_function
        
        return node_id

    def _parse_function_args(self, node: ast.FunctionDef, node_id: str) -> None:
        """解析函數參數"""
        args = []
        
        # 處理位置參數
        for arg in node.args.args:
            arg_info = {"name": arg.arg}
            if arg.annotation:
                if isinstance(arg.annotation, ast.Name):
                    arg_info["type"] = arg.annotation.id
            args.append(arg_info)
        
        # 處理預設參數
        defaults = node.args.defaults
        if defaults:
            offset = len(args) - len(defaults)
            for i, default in enumerate(defaults):
                index = offset + i
                if index < len(args):
                    args[index]["has_default"] = True
        
        # 將參數列表序列化為JSON字符串，而不是直接存儲字典
        self.nodes[node_id].properties["args"] = json.dumps(args)

    def _parse_import(self, node: Union[ast.Import, ast.ImportFrom]) -> None:
        """解析導入語句"""
        file_node_id = f"file:{self.current_file}"
        
        if isinstance(node, ast.Import):
            for name in node.names:
                import_name = name.name
                asname = name.asname or import_name
                
                # 添加到導入映射
                self.imports[asname] = import_name
                
                # 模組名稱（取第一部分，例如 'package.module' -> 'package'）
                root_module = import_name.split('.')[0]
                
                # 添加到待處理的導入依賴
                self.pending_imports.append({
                    "type": "IMPORTS_MODULE",
                    "source_id": file_node_id,
                    "imported_module": root_module,
                    "full_module_path": import_name,
                    "alias": asname
                })
        
        elif isinstance(node, ast.ImportFrom):
            module_name = node.module
            for name in node.names:
                import_name = name.name
                asname = name.asname or import_name
                
                # 添加到導入映射
                if module_name:
                    full_name = f"{module_name}.{import_name}"
                    self.imports[asname] = full_name
                else:
                    self.imports[asname] = import_name
                
                # 添加到待處理的導入依賴
                self.pending_imports.append({
                    "type": "IMPORTS_SYMBOL",
                    "source_id": file_node_id,
                    "imported_module": module_name,
                    "imported_name": import_name,
                    "alias": asname
                })

    def _parse_assignment(self, node: ast.Assign) -> None:
        """解析賦值語句"""
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                node_id = self._get_node_id("Variable", var_name, self.current_file, node.lineno)
                
                if self.current_class and not self.current_function:
                    # 類別屬性
                    self.nodes[node_id] = CodeNode(
                        node_id=node_id,
                        node_type="ClassVariable",
                        name=var_name,
                        file_path=self.current_file,
                        line_no=node.lineno,
                        end_line_no=getattr(node, "end_lineno", None),
                    )
                    
                    self.relations.append(
                        CodeRelation(
                            source_id=self.current_class,
                            target_id=node_id,
                            relation_type="DEFINES",
                        )
                    )
                elif self.current_function:
                    # 局部變數
                    self.nodes[node_id] = CodeNode(
                        node_id=node_id,
                        node_type="LocalVariable",
                        name=var_name,
                        file_path=self.current_file,
                        line_no=node.lineno,
                        end_line_no=getattr(node, "end_lineno", None),
                    )
                    
                    self.relations.append(
                        CodeRelation(
                            source_id=self.current_function,
                            target_id=node_id,
                            relation_type="DEFINES",
                        )
                    )
                else:
                    # 全局變數
                    self.nodes[node_id] = CodeNode(
                        node_id=node_id,
                        node_type="GlobalVariable",
                        name=var_name,
                        file_path=self.current_file,
                        line_no=node.lineno,
                        end_line_no=getattr(node, "end_lineno", None),
                    )
                    
                    file_node_id = f"file:{self.current_file}"
                    self.relations.append(
                        CodeRelation(
                            source_id=file_node_id,
                            target_id=node_id,
                            relation_type="DEFINES",
                        )
                    )

    def _parse_class_attribute(self, node: ast.Assign) -> None:
        """解析類別屬性"""
        # 與 _parse_assignment 類似，但專門處理類別內部的屬性
        for target in node.targets:
            if isinstance(target, ast.Name):
                var_name = target.id
                node_id = self._get_node_id("ClassVariable", var_name, self.current_file, node.lineno)
                
                self.nodes[node_id] = CodeNode(
                    node_id=node_id,
                    node_type="ClassVariable",
                    name=var_name,
                    file_path=self.current_file,
                    line_no=node.lineno,
                    end_line_no=getattr(node, "end_lineno", None),
                )
                
                self.relations.append(
                    CodeRelation(
                        source_id=self.current_class,
                        target_id=node_id,
                        relation_type="DEFINES",
                    )
                )

    def _find_function_calls(self, node: ast.AST) -> None:
        """在AST節點中尋找函數調用"""
        if isinstance(node, ast.Call):
            func = node.func
            
            if isinstance(func, ast.Name):
                # 直接函數調用
                func_name = func.id
                
                if func_name in self.imports:
                    # 處理導入的函數調用
                    imported_func = self.imports[func_name]
                    # 將調用添加到待處理隊列
                    if self.current_function:
                        self.pending_imports.append({
                            "type": "CALLS",
                            "source_id": self.current_function,
                            "imported_module": imported_func.split(".")[0] 
                                if "." in imported_func else imported_func,
                            "imported_name": imported_func.split(".")[-1] 
                                if "." in imported_func else imported_func,
                            "original_name": func_name
                        })
                elif self.current_function:
                    # 處理本地函數調用
                    self.relations.append(
                        CodeRelation(
                            source_id=self.current_function,
                            target_id=f"Function:{self.current_file}:{func_name}:0",  # 假設的目標ID
                            relation_type="CALLS",
                        )
                    )
            
            elif isinstance(func, ast.Attribute):
                # 調用物件的方法
                if isinstance(func.value, ast.Name):
                    obj_name = func.value.id
                    method_name = func.attr
                    
                    if obj_name in self.imports:
                        # 處理導入的類別/模組的方法調用
                        imported_obj = self.imports[obj_name]
                        # 將調用添加到待處理隊列
                        if self.current_function:
                            self.pending_imports.append({
                                "type": "CALLS_METHOD",
                                "source_id": self.current_function,
                                "imported_module": imported_obj.split(".")[0] 
                                    if "." in imported_obj else imported_obj,
                                "imported_class": imported_obj.split(".")[-1] 
                                    if "." in imported_obj else imported_obj,
                                "method_name": method_name,
                                "original_obj_name": obj_name
                            })
                    elif self.current_function:
                        # 處理本地物件方法調用
                        self.relations.append(
                            CodeRelation(
                                source_id=self.current_function,
                                target_id=f"Method:{self.current_file}:{method_name}:0",  # 假設的目標ID
                                relation_type="CALLS",
                                properties={"object": obj_name},
                            )
                        )
        
        # 遞迴查找嵌套的函數調用
        for child in ast.iter_child_nodes(node):
            self._find_function_calls(child)
            
    def _add_relation(self, relation: CodeRelation) -> None:
        """添加關係，避免重複"""
        # 創建關係的唯一標識
        relation_key = f"{relation.source_id}|{relation.relation_type}|{relation.target_id}"
        
        # 對於某些關係類型，還需要考慮屬性
        if relation.relation_type == "IMPORTS_FROM":
            # 對於導入關係，同一個檔案導入同一個模組只需記錄一次
            relation_key = f"{relation.source_id}|{relation.relation_type}|{relation.target_id}"
        elif relation.relation_type == "IMPORTS_DEFINITION":
            # 對於符號導入，需要考慮符號名稱
            symbol = relation.properties.get("symbol", "")
            relation_key = f"{relation.source_id}|{relation.relation_type}|{relation.target_id}|{symbol}"
        
        # 檢查是否已經存在相同的關係
        if relation_key not in self.established_relations:
            self.relations.append(relation)
            self.established_relations.add(relation_key)

    def _process_pending_imports(self) -> None:
        """處理所有待處理的導入關係"""
        print(f"處理跨檔案依賴關係，共 {len(self.pending_imports)} 項")
        
        # 先創建所有模組節點，將它們與檔案節點關聯
        for module_name, file_node_id in self.module_to_file.items():
            # 創建模組節點，但使用關聯到文件的ID
            # 注意：我們不再單獨創建重複的模組節點
            if file_node_id in self.nodes:
                file_node = self.nodes[file_node_id]
                file_node.properties["module_name"] = module_name
        
        # 按模組分組處理導入信息
        imports_by_source_module = {}
        for import_info in self.pending_imports:
            source_id = import_info["source_id"]
            if source_id not in imports_by_source_module:
                imports_by_source_module[source_id] = []
            imports_by_source_module[source_id].append(import_info)
        
        # 處理每個源文件的導入
        for source_id, imports in imports_by_source_module.items():
            # 跟踪已經處理過的模組導入
            processed_modules = set()
            
            for import_info in imports:
                import_type = import_info["type"]
                
                if import_type == "IMPORTS_MODULE":
                    # 檔案導入整個模組的情況
                    module_name = import_info["imported_module"]
                    
                    # 避免重複處理相同模組的導入
                    if module_name in processed_modules:
                        continue
                    processed_modules.add(module_name)
                    
                    # 查找模組對應的檔案節點
                    if module_name in self.module_to_file:
                        target_file_id = self.module_to_file[module_name]
                        
                        # 創建檔案間依賴關係
                        self._add_relation(
                            CodeRelation(
                                source_id=source_id,
                                target_id=target_file_id,
                                relation_type="IMPORTS_FROM",
                                properties={
                                    "module": module_name,
                                    "full_module_path": import_info.get("full_module_path", module_name)
                                }
                            )
                        )
                
                elif import_type == "IMPORTS_SYMBOL":
                    # 從模組導入特定符號的情況
                    module_name = import_info["imported_module"]
                    symbol_name = import_info["imported_name"]
                    
                    # 檢查模組定義索引
                    if module_name in self.module_definitions and symbol_name in self.module_definitions[module_name]:
                        target_node_id = self.module_definitions[module_name][symbol_name]
                        
                        # 創建檔案到符號的依賴關係
                        self._add_relation(
                            CodeRelation(
                                source_id=source_id,
                                target_id=target_node_id,
                                relation_type="IMPORTS_DEFINITION",
                                properties={
                                    "module": module_name,
                                    "symbol": symbol_name,
                                    "alias": import_info.get("alias")
                                }
                            )
                        )
                        
                        # 避免為已處理的模組重複創建IMPORTS_FROM關係
                        if module_name not in processed_modules and module_name in self.module_to_file:
                            processed_modules.add(module_name)
                            
                            # 創建到檔案的導入關係
                            self._add_relation(
                                CodeRelation(
                                    source_id=source_id,
                                    target_id=self.module_to_file[module_name],
                                    relation_type="IMPORTS_FROM",
                                    properties={
                                        "module": module_name,
                                        "imports_symbols": [symbol_name]
                                    }
                                )
                            )
                
                elif import_type == "EXTENDS":
                    # 類別繼承關係
                    module_name = import_info["imported_module"]
                    class_name = import_info["imported_name"]
                    
                    # 檢查模組定義索引
                    if module_name in self.module_definitions and class_name in self.module_definitions[module_name]:
                        target_node_id = self.module_definitions[module_name][class_name]
                        
                        # 創建繼承關係
                        self._add_relation(
                            CodeRelation(
                                source_id=source_id,
                                target_id=target_node_id,
                                relation_type="EXTENDS",
                                properties={"original_name": import_info.get("original_name")}
                            )
                        )
                
                elif import_type == "CALLS":
                    # 函數調用關係
                    module_name = import_info["imported_module"]
                    func_name = import_info["imported_name"]
                    
                    # 檢查模組定義索引
                    if module_name in self.module_definitions and func_name in self.module_definitions[module_name]:
                        target_node_id = self.module_definitions[module_name][func_name]
                        
                        # 創建調用關係
                        self._add_relation(
                            CodeRelation(
                                source_id=source_id,
                                target_id=target_node_id,
                                relation_type="CALLS",
                                properties={"original_name": import_info.get("original_name")}
                            )
                        )
                
                elif import_type == "CALLS_METHOD":
                    # 物件方法調用關係
                    module_name = import_info["imported_module"]
                    class_name = import_info["imported_class"]
                    method_name = import_info["method_name"]
                    
                    # 檢查模組定義索引中的類別
                    if module_name in self.module_definitions and class_name in self.module_definitions[module_name]:
                        class_node_id = self.module_definitions[module_name][class_name]
                        
                        # 尋找該類別定義的方法
                        for relation in self.relations:
                            if relation.source_id == class_node_id and relation.relation_type == "DEFINES":
                                target_node = self.nodes.get(relation.target_id)
                                if target_node and target_node.node_type == "Method" and target_node.name == method_name:
                                    # 創建調用關係
                                    self._add_relation(
                                        CodeRelation(
                                            source_id=source_id,
                                            target_id=relation.target_id,
                                            relation_type="CALLS",
                                            properties={
                                                "object": import_info.get("original_obj_name"),
                                                "class": class_name
                                            }
                                        )
                                    )
                                    break


# 使用範例
if __name__ == "__main__":
    parser = ASTParser()
    nodes, relations = parser.parse_file("example.py")
    
    print("找到的節點:")
    for node in nodes.values():
        print(f"  {node}")
    
    print("\n找到的關係:")
    for relation in relations:
        print(f"  {relation}") 