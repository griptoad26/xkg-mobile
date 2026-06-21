import 'package:flutter/material.dart';

class XKGSearchBar extends StatefulWidget {
  final Function(String) onSearch;

  const XKGSearchBar({
    super.key,
    required this.onSearch,
  });

  @override
  State<XKGSearchBar> createState() => _XKGSearchBarState();
}

class _XKGSearchBarState extends State<XKGSearchBar> {
  final TextEditingController _controller = TextEditingController();

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Container(
      decoration: BoxDecoration(
        color: const Color(0xFF12121A),
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: Colors.grey[800]!),
      ),
      child: TextField(
        controller: _controller,
        decoration: InputDecoration(
          hintText: 'Search XKG knowledge base...',
          hintStyle: TextStyle(color: Colors.grey[600]),
          prefixIcon: const Icon(Icons.search, color: Color(0xFF6366F1)),
          suffixIcon: IconButton(
            icon: const Icon(Icons.send, color: Color(0xFF6366F1)),
            onPressed: () {
              if (_controller.text.isNotEmpty) {
                widget.onSearch(_controller.text);
              }
            },
          ),
          border: InputBorder.none,
          contentPadding: const EdgeInsets.symmetric(
            horizontal: 16,
            vertical: 14,
          ),
        ),
        onSubmitted: widget.onSearch,
      ),
    );
  }
}
