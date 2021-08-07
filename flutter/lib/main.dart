import 'package:flutter/material.dart';
import 'dart:async';
import 'dart:convert';
import 'dart:io';
import 'package:http/http.dart' as http;


Future<String> getHello() async {
  // var url = 'http://127.0.0.1:5000/name/backupy';
  // final response = await http.get(url);
  final response = await http.post(
    'http://127.0.0.1:5000/args/',
    headers: <String, String>{'Content-Type': 'application/json; charset=UTF-8'},
    body: jsonEncode({'arg1': 'world', 'arg2': true})
  );
  if (response.statusCode == 200) {
    // var jsonResponse = convert.jsonDecode(response.body);
    // return jsonResponse;
    return response.body;
  } else {
    return null;
  }
}


Future main() async {
  Process.start('./venv/bin/python', ['flutter_flask.py'], mode: ProcessStartMode.normal).then((process){
    stdout.addStream(process.stdout);
    stderr.addStream(process.stderr);
  });
  runApp(MyApp());
}

//void main() => runApp(MyApp());

class MyApp extends StatefulWidget {
  MyApp({Key key}) : super(key: key);

  @override
  _MyAppState createState() => _MyAppState();
}

class _MyAppState extends State<MyApp> with WidgetsBindingObserver {
  Future<String> futureText;

  @override
  void initState() {
    super.initState();
    futureText = getHello();
  }
  @override
  void dispose() {
    http.get('http://127.0.0.1:5000/terminate');
    super.dispose();
  }
  @override
  void didChangeAppLifecycleState(AppLifecycleState state){
      if (state == AppLifecycleState.detached){
        http.get('http://127.0.0.1:5000/terminate');
      }
  }
  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      title: 'Welcome to Flutter',
      home: Scaffold(
        appBar: AppBar(
          title: Text('Welcome to Flutter'),
        ),
        body: Center(
          child: FutureBuilder<String>(
            future: futureText,
            builder: (context, snapshot) {
              if (snapshot.hasData) {
                return Text(snapshot.data.toString());
              } else if (snapshot.hasError) {
                return Text("${snapshot.error}");
              }
              // By default, show a loading spinner.
              return CircularProgressIndicator();
            },
          ),
        ),
      ),
    );
  }
}
