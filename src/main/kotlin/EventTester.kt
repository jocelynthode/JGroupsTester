import org.jgroups.*
import java.net.InetAddress
import java.util.*

/**
 * This Class connects to a cluster, waits for other peers to join and then sends a number of events
 *
 * This implementation uses the SEQUENCER Channel. This uses Total Order and UDP
 *
 * @author Jocelyn Thode
 */

class EventTester : ReceiverAdapter() {

    var channel = JChannel("sequencer.xml")
    val MAX_EVENTS_SENT = 12
    val TIME_TO_WAIT = 120000L
    val TOTAL_MESSAGES = 250 * MAX_EVENTS_SENT
    var deliveredMessages = 0

    fun start() {
        channel.receiver = this
        channel.connect("EventCluster")
        var eventsSent = 0
        println(channel.address.toString())

        // Give time for all peers to join //TODO verify it doesn't block
        Thread.sleep(TIME_TO_WAIT)
        while(eventsSent != MAX_EVENTS_SENT) {
	    val msg = Message(null, null, "${UUID.randomUUID()}")
            channel.send(msg)
            eventsSent++
	    //println("Sent: ${msg.src} : ${msg.`object`}")
            Thread.sleep(1000)
        }
	println(eventsSent)
        //channel.close()
    }

    override fun viewAccepted(newView: View) {
        println("** size: ${newView.size()} ** view: $newView")

    }

    override fun receive(msg: Message) {
        println("${msg.src} : Delivered ${msg.`object`}")
        deliveredMessages++
        if (deliveredMessages >= TOTAL_MESSAGES) {
            println("All messages have been delivered !")
            System.exit(0)
        }

    }
}

fun main(args: Array<String>){
    val eventTester = EventTester()
    eventTester.start()
    while(true) Thread.sleep(500)
}
