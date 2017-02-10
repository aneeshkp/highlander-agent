var server =require("websocket").server
var http = require('http');
var libvirt=require('libvirt')
var hypervisor_object=new libvirt.Hypervisor("qemu:///system")

var socket=new server({
httpServer:http.createServer(function(request,response){}).listen(3001,function(){console.log("Server is listening")})
});

hypervisor_object.connect(function(err){
if(!err){
console.log("Virsh connected")
}else{
console.log("Virish connection failed");
}
});
socket.on('request',function(request){
      var connection=request.accept(null,request.origin);
      console.log("connection accepted")

      connection.on('message',function(message){
      console.log("message received")
      var returnjson={};

      hypervisor_object.listActiveDomains(function(err,info){
      returnjson.data=info;
      });
      returnjson.time=new Date().getTime();

      connection.sendUTF(JSON.stringify(returnjson))
      var id = setInterval(function(){
                  hypervisor_object.listActiveDomains(function(err,info){
      returnjson.data=info;
      });
      returnjson.time=new Date().getTime();

      connection.sendUTF(JSON.stringify(returnjson))
          }, 0.01);
     });
});

