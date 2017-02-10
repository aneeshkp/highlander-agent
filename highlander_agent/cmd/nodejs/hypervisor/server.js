var server =require("websocket").server

var http = require('http');

var uimonitor_connection=null;

var socket=new server({
httpServer:http.createServer(function(request,response){}).listen(3000,function(){console.log("[1]Server is listening for heart beat at 3000")})
});

var socket_agent=new server({
httpServer:http.createServer(function(request,response){}).listen(3001,function(){console.log("[2]Server is listening for agents at 3001")})
});

var socket_monitor=new server({
httpServer:http.createServer(function(request,response){}).listen(3002,function(){console.log("[3]UI Server is listening at port 3002")})


});

socket.on('request',function(request){
      var connection=request.accept(null,request.origin);
      console.log("monitor connection accepted")
      connection.on('message',function(message){
      console.log("message received")
      connection.sendUTF(new Date().getTime())
      var id = setInterval(function(){
            connection.sendUTF(new Date().getTime())
          }, 0.01);
     });

});

socket_agent.on('request',function(request){
      var connection=request.accept(null,request.origin);
      console.log("monitor connection accepted")
      connection.on('message',function(message){
      console.log("message received")
      //forward it to dash board
      if (uimonitor_connection!=null){
      try{
         var parseddata= JSON.stringify(JSON.parse(message.utf8Data))
         console.log(parseddata);
         uimonitor_connection.send(parseddata);
       } catch(err){
          console.log("There was an error",err);
       }

       }else{
       console.log("no client registered");}
      });
     });

socket_monitor.on('request',function(request){
      var connection=request.accept(null,request.origin);
      console.log("connection accepted")
      uimonitor_connection=connection;
      connection.on('close',function(request){
           console.log("Ui client disconnected");
         uimonitor_connection=null
         console.log("Ui client disconnected");
       });
      connection.on('message',function(message){
      console.log("message received")

     });
});

